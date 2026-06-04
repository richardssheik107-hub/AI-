import re
import time
import uuid
from collections import deque


class HandoffService:
    def __init__(self):
        self.tickets = deque(maxlen=100)
        self.rules = [
            {
                "id": "unauthorized_transaction",
                "category": "交易安全/疑似盗刷",
                "priority": "high",
                "patterns": [
                    ["不是本人交易"],
                    ["不是我刷"],
                    ["不是我消费"],
                    ["非本人交易"],
                    ["盗刷"],
                    ["异常交易"],
                    ["卡被刷"],
                ],
                "action": "transfer_human",
                "answer": "这属于账户安全高风险问题。建议您立即通过官方 App 或客服电话挂失、冻结或登记争议交易工单，请不要提供验证码、密码或卡片安全码。",
            },
            {
                "id": "fee_dispute",
                "category": "费用争议/投诉工单",
                "priority": "medium",
                "patterns": [
                    ["乱扣费"],
                    ["扣错费"],
                    ["多扣费"],
                    ["费用", "投诉"],
                    ["扣费", "工单"],
                    ["费用", "争议"],
                    ["我要投诉"],
                    ["马上投诉"],
                ],
                "action": "create_ticket",
                "answer": "我已为您生成费用争议工单记录。建议准备发生时间、争议金额和相关账单信息，后续通过官方 App 或人工客服继续核实处理。请不要提供验证码、密码等敏感信息。",
            },
            {
                "id": "credit_dispute",
                "category": "征信异议/人工核查",
                "priority": "medium",
                "patterns": [
                    ["征信", "删"],
                    ["征信", "删除"],
                    ["征信", "异议"],
                    ["逾期记录", "删"],
                    ["上报", "错"],
                ],
                "action": "transfer_human",
                "answer": "征信记录无法由智能客服直接修改或删除。如您认为记录有误，建议通过官方 App 或人工客服提交征信异议核查。",
            },
            {
                "id": "manual_request",
                "category": "人工服务",
                "priority": "normal",
                "patterns": [
                    ["转人工"],
                    ["人工客服"],
                    ["找人工"],
                    ["真人客服"],
                ],
                "action": "transfer_human",
                "answer": "我已记录您的人工服务需求。请通过官方 App 或客服电话继续转接人工客服处理。",
            },
        ]

    def normalize(self, text: str) -> str:
        return re.sub(r"\s+", "", (text or "").strip().lower())

    def match(self, question: str) -> dict | None:
        normalized = self.normalize(question)
        if not normalized:
            return None

        for rule in self.rules:
            for pattern in rule["patterns"]:
                if all(keyword in normalized for keyword in pattern):
                    return rule

        return None

    def create_ticket(self, question: str, rule: dict) -> dict:
        ticket = {
            "ticket_id": f"TK-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            "created_at": int(time.time()),
            "category": rule["category"],
            "priority": rule["priority"],
            "action": rule["action"],
            "rule_id": rule["id"],
            "question": question,
            "status": "created",
            "answer": rule["answer"],
        }
        self.tickets.appendleft(ticket)
        return ticket

    def try_create(self, question: str) -> dict | None:
        rule = self.match(question)
        if not rule:
            return None
        return self.create_ticket(question, rule)

    def recent(self, limit: int = 20) -> list[dict]:
        return list(self.tickets)[: max(1, min(limit, 100))]


handoff_service = HandoffService()
