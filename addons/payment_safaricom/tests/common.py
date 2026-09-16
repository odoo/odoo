# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch

from odoo.fields import Command

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


class SafaricomCommon(PaymentHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency = cls._enable_currency("KES")
        cls.provider = cls._prepare_provider(
            "safaricom",
            update_values={
                "safaricom_consumer_key": "WIE6GXsAoGDa4AZ8AsVFq06NSQZwyTZB85y7xjj9Nij6Rom6",
                "safaricom_consumer_secret": (
                    "Yh9GpjTcrPj2L2v8Bo9PFOlGEAk5SWKMqQiMVGN9pTDJfMxtyZfvkxGy4Vj11cls"
                ),
                "safaricom_passkey": (
                    "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
                ),
                "safaricom_shortcode": "174379",
                "safaricom_transaction_type": "CustomerPayBillOnline",
                "available_currency_ids": [Command.set([cls.currency.id])],
            },
        )
        cls.payment_method_id = cls.provider.payment_method_ids[:1].id
        cls.amount = 1111.0
        cls.timestamp = "20231118120000"
        cls.phone = "254708374149"

        cls.checkout_id = "ws_CO_20231118120000000123456789"
        cls.webhook_payment_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": cls.checkout_id,
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": cls.amount},
                            {"Name": "MpesaReceiptNumber", "Value": "LHG31AA5TX"},
                            {"Name": "TransactionDate", "Value": int(cls.timestamp)},
                            {"Name": "PhoneNumber", "Value": int(cls.phone)},
                        ]
                    },
                }
            }
        }

    @contextmanager
    def _mock_send_api_request(self, return_value):
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value=return_value,
        ) as mock:
            yield mock

    def _get_stk_push_params(self, tx, **overrides):
        return {
            "reference": tx.reference,
            "phone": self.phone,
            "access_token": payment_utils.generate_access_token(tx.reference, env=self.env),
            **overrides,
        }
