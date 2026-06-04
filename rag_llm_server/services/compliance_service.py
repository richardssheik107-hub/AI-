import re


class ComplianceService:
    def __init__(self):
        self.rules = [
            {
                "id": "sms_code",
                "risk_type": "verification_code",
                "patterns": [
                    re.compile(r"(验证码|校验码|短信码|动态码).{0,12}(发给你|告诉你|报给你|给你|帮我输入|帮我处理)"),
                    re.compile(r"\b\d{4,8}\b.*(验证码|校验码|短信码|动态码)"),
                    re.compile(r"(验证码|校验码|短信码|动态码).*\b\d{4,8}\b"),
                ],
                "answer": "请不要向任何人提供短信验证码。验证码、密码、CVV 都属于敏感信息，建议您通过官方 App 或人工客服按安全流程处理。",
            },
            {
                "id": "password",
                "risk_type": "password",
                "patterns": [
                    re.compile(r"(密码|支付密码|登录密码).{0,12}(发给你|告诉你|报给你|给你|帮我输入)"),
                    re.compile(r"(我的密码是|支付密码是|登录密码是)"),
                ],
                "answer": "请不要提供密码。密码、验证码、CVV 都属于敏感信息，建议您立即停止透露，并通过官方 App 或人工客服处理。",
            },
            {
                "id": "bank_card_number",
                "risk_type": "bank_card",
                "patterns": [
                    re.compile(r"\b\d{13,19}\b"),
                    re.compile(r"(银行卡号|卡号).{0,8}\d{8,19}"),
                ],
                "answer": "请不要在语音中提供完整银行卡号。银行卡号、验证码、密码、CVV 都属于敏感信息，建议通过官方 App 或人工客服核实。",
            },
            {
                "id": "id_card_number",
                "risk_type": "id_card",
                "patterns": [
                    re.compile(r"\b\d{17}[\dXx]\b"),
                    re.compile(r"(身份证号|证件号).{0,8}\d{10,18}"),
                ],
                "answer": "请不要在语音中提供完整身份证号。证件号、验证码、密码、CVV 都属于敏感信息，建议通过官方 App 或人工客服完成身份核验。",
            },
            {
                "id": "card_security_code",
                "risk_type": "cvv",
                "patterns": [
                    re.compile(r"(CVV|CVC|安全码|卡背后三位).{0,12}(发给你|告诉你|报给你|给你|是)"),
                ],
                "answer": "请不要提供 CVV、CVC 或卡片安全码。这些属于敏感信息，建议您通过官方 App 或人工客服按安全流程处理。",
            },
        ]

    def check(self, text: str) -> dict | None:
        normalized = (text or "").strip()
        if not normalized:
            return None

        compact = re.sub(r"\s+", "", normalized)
        for rule in self.rules:
            if any(pattern.search(compact) for pattern in rule["patterns"]):
                return {
                    "id": rule["id"],
                    "risk_type": rule["risk_type"],
                    "answer": rule["answer"],
                    "source": "safety_direct",
                }

        return None


compliance_service = ComplianceService()
