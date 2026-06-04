import copy
import httpx
import re
import time
from collections import OrderedDict

from config import settings
from services.utils import Signer


class RagService:
    def __init__(self):
        # 1. 加载基础鉴权配置
        self.ak = settings.VOLC_AK
        self.sk = settings.VOLC_SK
        
        # 2. 知识库特有配置
        self.collection_name = settings.KB_COLLECTION_NAME
        self.project_name = settings.KB_PROJECT_NAME
        self.account_id = settings.VOLC_ACCOUNT_ID
        self.default_limit = max(1, settings.KB_SEARCH_LIMIT)
        self.max_context_chars = max(500, settings.KB_MAX_CONTEXT_CHARS)
        self.timeout = max(1.0, settings.KB_REQUEST_TIMEOUT)
        self.cache_ttl_seconds = max(0, settings.KB_CACHE_TTL_SECONDS)
        self.cache_max_size = max(0, settings.KB_CACHE_MAX_SIZE)
        self._cache = OrderedDict()
        
        # 知识库服务的固定配置
        self.host = "api-knowledgebase.mlp.cn-beijing.volces.com"
        self.region = "cn-north-1" # 示例代码中使用的是 cn-north-1
        self.service = "air"       # 知识库服务的 Service 名通常为 air

    def _normalize_query(self, query: str) -> str:
        return re.sub(r"\s+", "", (query or "").strip().lower())

    def _cache_key(self, query: str, limit: int) -> tuple:
        return (
            self.project_name,
            self.collection_name,
            limit,
            self.max_context_chars,
            self._normalize_query(query),
        )

    def _get_cached_result(self, cache_key: tuple) -> dict | None:
        if self.cache_ttl_seconds <= 0 or self.cache_max_size <= 0:
            return None

        cached = self._cache.get(cache_key)
        if not cached:
            return None

        cached_at, result = cached
        if time.time() - cached_at > self.cache_ttl_seconds:
            self._cache.pop(cache_key, None)
            return None

        self._cache.move_to_end(cache_key)
        result_copy = copy.deepcopy(result)
        result_copy["cache_hit"] = True
        result_copy["cache_ttl_seconds"] = self.cache_ttl_seconds
        return result_copy

    def _set_cached_result(self, cache_key: tuple, result: dict) -> None:
        if self.cache_ttl_seconds <= 0 or self.cache_max_size <= 0:
            return

        cached_result = copy.deepcopy(result)
        cached_result["cache_hit"] = False
        cached_result["cache_ttl_seconds"] = self.cache_ttl_seconds
        self._cache[cache_key] = (time.time(), cached_result)
        self._cache.move_to_end(cache_key)

        while len(self._cache) > self.cache_max_size:
            self._cache.popitem(last=False)

    async def search(self, query: str, limit: int | None = None) -> dict:
        """
        根据用户问题检索知识库，并返回结构化结果，便于调试命中质量。
        :param query: 用户查询语句
        :param limit: 本次检索条数；不传则使用 KB_SEARCH_LIMIT
        :return: 包含 context、items、status 的结构化结果
        """
        query = (query or "").strip()
        if not query:
            return {
                "status": "empty_query",
                "context": "",
                "items": [],
                "limit": 0,
                "context_length": 0,
            }

        # 基础校验
        if not self.ak or not self.sk or not self.account_id:
            print(f"[RagService] Missing config: check VOLC_AK, VOLC_SK, VOLC_ACCOUNT_ID(current: {self.account_id})")
            return {
                "status": "missing_config",
                "context": "",
                "items": [],
                "limit": 0,
                "context_length": 0,
            }

        path = "/api/knowledge/collection/search_knowledge"
        search_limit = max(1, min(int(limit or self.default_limit), 10))
        cache_key = self._cache_key(query, search_limit)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            print(f"[RagService] Cache hit: {cache_key[-1]}")
            return cached_result
        
        # 3. 构造请求体 (参考官方示例)
        body = {
            "project": self.project_name,
            "name": self.collection_name,
            "query": query,
            "limit": search_limit,
            "pre_processing": {
                "need_instruction": True,
                "return_token_usage": True,
                "messages": [{"role": "user", "content": query}]
            },
            "post_processing": {
                "get_attachment_link": True
            }
        }

        # 4. 构造 Header
        # 注意：V-Account-Id 是知识库接口必须的
        headers = {
            "Host": self.host,
            "Content-Type": "application/json",
            "V-Account-Id": self.account_id 
        }

        # 构造待签名的请求数据
        request_data = {
            "method": "POST",
            "path": path,
            "headers": headers,
            "body": body,
            "params": {}
        }



        try:
            # 5. 计算签名 (复用 utils.py 中的 Signer)
            # 知识库使用的是 air / cn-north-1
            signer = Signer(request_data, service=self.service, region=self.region)
            signer.add_authorization({
                "accessKeyId": self.ak,
                "secretKey": self.sk
            })
            
            # 6. 发送异步请求
            url = f"http://{self.host}{path}"
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, 
                    headers=request_data["headers"], 
                    json=body,
                    timeout=self.timeout
                )

            # 6. 解析响应内容
            if resp.status_code != 200:
                print(f"[RagService] Request failed: {resp.status_code}, {resp.text}")
                return {
                    "status": "request_failed",
                    "http_status": resp.status_code,
                    "context": "",
                    "items": [],
                    "limit": search_limit,
                    "context_length": 0,
                }

            data = resp.json()
            result_list = data.get("data", {}).get("result_list", [])

            items = []
            for index, item in enumerate(result_list, start=1):
                content = (item.get("content") or "").strip()
                if not content:
                    continue
                items.append(
                    {
                        "rank": index,
                        "content": content,
                        "content_length": len(content),
                        "score": item.get("score"),
                        "doc_id": item.get("doc_id") or item.get("id"),
                        "doc_name": item.get("doc_name") or item.get("title") or item.get("name"),
                    }
                )

            if not items:
                print("[RagService] No matched knowledge content")
                result = {
                    "status": "no_results",
                    "context": "",
                    "items": [],
                    "limit": search_limit,
                    "context_length": 0,
                    "cache_hit": False,
                }
                self._set_cached_result(cache_key, result)
                return result

            blocks = []
            current_length = 0
            for item in items:
                block = f"[知识片段 {item['rank']}]\n{item['content']}"
                if blocks and current_length + len(block) > self.max_context_chars:
                    break
                blocks.append(block)
                current_length += len(block)

            context_text = "\n\n".join(blocks)
            
            print(f"[RagService] Retrieved {len(items)} item(s), using {len(blocks)} block(s)")
            print(f"[RagService] Context length: {len(context_text)} chars")
            result = {
                "status": "success",
                "context": context_text,
                "items": items,
                "limit": search_limit,
                "used_blocks": len(blocks),
                "context_length": len(context_text),
                "max_context_chars": self.max_context_chars,
                "cache_hit": False,
                "cache_ttl_seconds": self.cache_ttl_seconds,
            }
            self._set_cached_result(cache_key, result)
            return result


        except Exception as e:
            print(f"[RagService] Exception: {e}")
            return {
                "status": "exception",
                "error": str(e),
                "context": "",
                "items": [],
                "limit": limit or self.default_limit,
                "context_length": 0,
            }

    async def retrieve(self, query: str) -> str:
        """
        根据用户问题检索知识库，返回拼接后的上下文文本，供 LLM 语音链路直接使用。
        """
        result = await self.search(query)
        return result.get("context", "")

# 实例化单例
rag_service = RagService()
