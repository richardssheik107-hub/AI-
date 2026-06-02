import os
from volcenginesdkarkruntime import Ark 
from config import settings

class LLMService:
    def __init__(self):
        api_key = settings.ARK_API_KEY 
        self.client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",    
            api_key=api_key,
            ak=settings.VOLC_AK,
            sk=settings.VOLC_SK,
            timeout=1800, 

        )

    def chat_stream(self, history_messages: list, rag_context: str = ""):
        """
        流式对话
        :param history_messages: 对话历史
        :param rag_context: 从 rag_service 检索出来的背景知识
        """
        if not self.client:
            yield "服务配置错误"
            return

        # 语音通话场景要求首句快、句子短、信息密度高，避免 TTS 播报过长。
        system_content = """
        # 角色
        你是【小宁】，一名信用卡与消费金融业务智能语音客服。你的表达自然、简短、稳妥，能解释一般规则、提示风险，并在高风险场景引导用户转人工。

        # 核心任务
        1. 优先依据【参考知识库】回答信用卡和消费金融咨询，包括账单、还款、分期、逾期、额度、费用、交易安全、贷款和投诉工单。
        2. 知识库有明确内容时，只解释一般规则和处理路径，不要编造用户个人账户信息、审批结果、费率、减免结论或征信结论。
        3. 涉及个人账户明细、费用争议、盗刷诈骗、征信异议、投诉、身份核验失败或用户情绪激烈时，必须建议转人工或登记工单。

        # 安全与合规边界
        - 不要要求用户提供完整身份证号、完整银行卡号、短信验证码、登录密码、支付密码、CVV/CVC 或卡片安全码。
        - 不要承诺一定提额、一定放款、一定减免费用、一定不上征信或删除征信记录。
        - 涉及金额、费率、账单、剩余欠款、额度、审批结果时，必须提示以 App、合同、账单或人工核验结果为准。
        - 如果用户主动说出敏感信息，要提醒用户不要继续提供完整敏感信息。

        # 语音回复规则
        - 回答必须适合直接被 TTS 朗读。
        - 每次回复控制在 2 到 4 句话，尽量不超过 100 个汉字。
        - 多用短句，少用书面语，不要输出复杂列表、Markdown、编号或表格。
        - 先给结论，再补一句关键依据，最后可以自然追问一句。

        # 兜底话术
        如果参考知识库没有相关内容，请回复：
        “这个问题我暂时没有查到准确信息。为了避免误导您，建议通过官方 App 或人工客服进一步确认。”
                """.strip()

        # --- 2. 构造最终发送给模型的消息序列 ---
        # messages = [{"role": "system", "content": system_content}]

        system_blocks = [system_content]

        if rag_context:
            # 使用明确的定界符，帮助模型在毫秒内定位知识
            system_blocks.append(f"### 参考知识库（绝对准则）\n{rag_context.strip()}")
        else:
            system_blocks.append("### 参考知识库（绝对准则）\n本轮没有检索到可用知识。请执行兜底话术，不要编造金融业务规则或个人账户信息。")

        # 合并为一条
        final_system_prompt = "\n\n".join(system_blocks)

        # 最终的消息序列
        messages = [{"role": "system", "content": final_system_prompt}]

        # 加入历史对话（确保包含用户最新的问题）
        messages.extend(history_messages)

        try:
            print(f"Start streaming call (Endpoint: {settings.ARK_ENDPOINT_ID})")
            
            stream = self.client.chat.completions.create(
                model=settings.ARK_ENDPOINT_ID,
                messages=messages,
                temperature=0.3, # 降低随机性，确保回答更严谨地贴合 RAG
                stream=True,
                stream_options={"include_usage": True},
            )

            for chunk in stream:
                yield chunk

        except Exception as e:
            print(f"LLM call failed: {e}")
            yield None

llm_service = LLMService()
