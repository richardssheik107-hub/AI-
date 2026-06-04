from volcenginesdkarkruntime import Ark
from config import settings


class LLMService:
    def __init__(self):
        self.client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=settings.ARK_API_KEY,
            ak=settings.VOLC_AK,
            sk=settings.VOLC_SK,
            timeout=1800,
        )

    def chat_stream(self, history_messages: list, rag_context: str = ""):
        """
        Stream chat completion chunks.

        history_messages must include the latest user question.
        rag_context is the retrieved knowledge base context.
        """
        if not self.client:
            yield "LLM service config error"
            return

        system_content = """
你是“小宁”，信用卡与消费金融语音客服。
只根据【参考知识库】回答；没有相关知识就说：“这个问题我暂时没有查到准确信息。为了避免误导您，建议通过官方 App 或人工客服进一步确认。”
回答要求：
- 适合直接朗读，最多 2 句话，尽量 60 字以内。
- 先给结论，再说关键处理建议。
- 不编造账户信息、审批结果、利率、减免或征信结论。
- 不索要完整身份证号、银行卡号、验证码、密码、CVV/CVC。
- 盗刷、投诉、征信异议、费用争议等高风险问题，引导转人工或登记工单。
""".strip()

        if rag_context:
            knowledge_block = f"【参考知识库】\n{rag_context.strip()}"
        else:
            knowledge_block = "【参考知识库】\n本轮没有检索到可用知识。请执行兜底话术。"

        messages = [
            {
                "role": "system",
                "content": f"{system_content}\n\n{knowledge_block}",
            }
        ]
        messages.extend(history_messages)

        try:
            print(
                "Start streaming call "
                f"(Endpoint: {settings.ARK_ENDPOINT_ID}, "
                f"max_tokens: {settings.ARK_MAX_TOKENS}, "
                f"service_tier: {settings.ARK_SERVICE_TIER}, "
                f"reasoning_effort: {settings.ARK_REASONING_EFFORT})"
            )

            request_kwargs = {
                "model": settings.ARK_ENDPOINT_ID,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": settings.ARK_MAX_TOKENS,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if settings.ARK_SERVICE_TIER:
                request_kwargs["service_tier"] = settings.ARK_SERVICE_TIER
            if settings.ARK_REASONING_EFFORT:
                request_kwargs["reasoning_effort"] = settings.ARK_REASONING_EFFORT

            try:
                stream = self.client.chat.completions.create(**request_kwargs)
            except Exception as optimized_error:
                if not (settings.ARK_SERVICE_TIER or settings.ARK_REASONING_EFFORT):
                    raise

                print(f"LLM optimized request failed, retrying without service_tier: {optimized_error}")
                request_kwargs.pop("service_tier", None)
                try:
                    stream = self.client.chat.completions.create(**request_kwargs)
                except Exception as reasoning_error:
                    print(
                        "LLM reasoning_effort request failed, "
                        f"retrying without reasoning_effort: {reasoning_error}"
                    )
                    request_kwargs.pop("reasoning_effort", None)
                    stream = self.client.chat.completions.create(**request_kwargs)

            for chunk in stream:
                yield chunk

        except Exception as e:
            print(f"LLM call failed: {e}")
            yield None


llm_service = LLMService()
