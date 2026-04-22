# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.addons.payment.tests.common import PaymentCommon


class QFPayCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.qfpay = cls._prepare_provider(
            "qfpay",
            update_values={"qfpay_app_code": "mock-app-code", "qfpay_app_key": "mock-app-key"},
        )
        cls.provider = cls.qfpay
        cls.payment_method = cls.env.ref("payment_qfpay.payment_method_card")
        cls.payment_method_id = cls.payment_method.id
        cls.payment_method_code = cls.payment_method.code
        cls.currency = cls._enable_currency("HKD")

        cls.mock_intent_response = {"respcd": "0000", "payment_intent": "mock-payment-intent-token"}
        cls.payment_data = {
            "out_trade_no": cls.reference,
            "txamt": "111111",
            "txcurrcd": "HKD",
            "pay_type": "802801",
            "syssn": "20261113000200020000000001",
            "respcd": "0000",
        }
        cls.webhook_data = {**cls.payment_data, "notify_type": "payment"}
        cls.webhook_raw_body = json.dumps(cls.webhook_data).encode("utf-8")
        cls.webhook_signature = "5ED34AB65B1BD6B38F0C5E585C003F08"
