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
        cls.currency = cls._enable_currency("HKD")

        cls.mock_intent_response = {
            "respcd": "0000",
            "payment_intent": "mock-payment-intent-token",
            "intent_expiry": "2026-12-31 23:59:59",
        }
        cls.webhook_data = {
            "out_trade_no": cls.reference,
            "txamt": str(int(cls.amount * 100)),
            "txcurrcd": cls.currency.name,
            "respcd": "0000",
            "respmsg": "Success",
        }
        cls.webhook_raw_body = json.dumps(cls.webhook_data).encode("utf-8")
        cls.webhook_signature = cls.provider._qfpay_calculate_signature(
            signing_string=cls.webhook_raw_body
        )
