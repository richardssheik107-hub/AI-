import re


class FAQService:
    def __init__(self):
        self.rules = [
            {
                "id": "late_one_day_credit",
                "patterns": [
                    ["晚还", "一天", "征信"],
                    ["迟还", "一天", "征信"],
                    ["逾期", "一天", "征信"],
                    ["晚了", "一天", "征信"],
                    ["超过还款日", "一天", "征信"],
                    ["迟还", "一天", "信用"],
                    ["晚还", "一天", "信用"],
                    ["逾期", "一天", "信用"],
                    ["晚了", "一天", "还款"],
                    ["晚了一天", "还款"],
                ],
                "answer": "是否影响征信要看银行入账时间、容时政策和账户状态。建议您尽快还款，并通过官方 App 或人工客服核实账户状态。",
            },
            {
                "id": "minimum_payment_credit",
                "patterns": [
                    ["最低还款", "征信"],
                    ["最低还款", "逾期"],
                    ["还最低", "征信"],
                    ["还最低", "影响"],
                    ["最低额", "征信"],
                ],
                "answer": "一般在到期还款日前按账单要求还足最低还款额，通常不会被认定为逾期。是否影响征信仍要以银行实际上报规则和账户状态为准。",
            },
            {
                "id": "card_lost",
                "patterns": [
                    ["信用卡", "丢"],
                    ["信用卡", "遗失"],
                    ["信用卡", "找不到"],
                    ["卡片", "找不到"],
                    ["卡", "丢了"],
                    ["卡", "找不到"],
                    ["卡片", "丢"],
                    ["卡", "挂失"],
                ],
                "answer": "建议您立即通过银行 App 或官方客服电话办理挂失，避免卡片被他人使用。挂失后如需补卡，可按系统提示申请补卡。",
            },
            {
                "id": "fraud_trade",
                "patterns": [
                    ["不是本人交易"],
                    ["不是我刷"],
                    ["不是我消费"],
                    ["非本人交易"],
                    ["交易", "不是本人"],
                    ["消费", "不是本人"],
                ],
                "answer": "为了保护账户安全，建议您立即通过官方 App 或客服电话进行挂失、冻结或争议登记。请不要向任何人提供验证码、密码或卡片安全码。",
            },
            {
                "id": "fraud_swipe",
                "patterns": [
                    ["盗刷"],
                    ["被刷了"],
                    ["卡被刷"],
                    ["疑似盗刷"],
                    ["异常交易"],
                ],
                "answer": "发现疑似盗刷时，建议您立即通过官方 App 或客服电话进行挂失、冻结或争议登记。请保留交易短信和相关凭证，并不要提供验证码或密码。",
            },
            {
                "id": "complaint_fee",
                "patterns": [
                    ["乱扣费"],
                    ["扣错费"],
                    ["多扣费"],
                    ["费用", "投诉"],
                    ["扣费", "工单"],
                    ["费用", "争议"],
                ],
                "answer": "涉及费用争议或乱扣费，建议您通过官方 App、客服电话或人工客服登记工单。您可以准备发生时间、争议金额和相关账单信息进行核实。",
            },
            {
                "id": "complaint_ticket",
                "patterns": [
                    ["投诉", "工单"],
                    ["投诉", "登记"],
                    ["投诉", "处理"],
                    ["人工", "投诉"],
                    ["我要投诉"],
                ],
                "answer": "涉及投诉或工单登记，建议您通过官方 App、客服电话或人工客服提交。您可以准备发生时间、争议金额和相关交易信息协助核实。",
            },
        ]

    def normalize(self, text: str) -> str:
        text = (text or "").strip().lower()
        return re.sub(r"\s+", "", text)

    def match(self, question: str) -> dict | None:
        normalized = self.normalize(question)
        if not normalized:
            return None

        for rule in self.rules:
            for pattern in rule["patterns"]:
                if all(keyword in normalized for keyword in pattern):
                    return rule

        return None


faq_service = FAQService()
