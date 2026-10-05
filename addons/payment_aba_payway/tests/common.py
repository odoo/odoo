# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class AbaPaywayCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.aba_payway = cls._prepare_provider(
            "aba_payway",
            update_values={
                "aba_payway_merchant_id": "ec000002",
                "aba_payway_api_key": "aba_payway_api_key",
            },
        )
        cls.payment_method_card = cls.aba_payway._get_pm_from_code("card")
        cls.provider = cls.aba_payway
        cls.payment_method_id = cls.payment_method_card.id
        cls.amount = 2213
        cls.currency = cls._enable_currency("KHR")
        cls.webhook_payment_data_signature = (
            "UP8bu1hTc26Lmbvypcsc1victE12EIG1H29w2bRF9b4Qibl4/"
            "DWOJaasgvyRUJ+/PWqrvBSBOXpcyBnT0Irl6w=="
        )
        cls.webhook_payment_data = {
            "tran_id": cls.reference,
            "apv": "544415",
            "status": "0",
            "original_amount": float(cls.amount),  # Sent as a float by ABA PayWay
            "original_currency": cls.currency.name,
            "payment_amount": float(cls.amount),
            "payment_currency": cls.currency.name,
            "total_amount": float(cls.amount),
            "discount_amount": 0,
            "transaction_date": "2026-08-03 13:57:20",
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone": "",
            "bank_ref": "100FT40074059022",
            "payment_type": "ABA Pay",
            "payer_account": "003471222",
            "bank_name": "ABA Bank",
            "card_source": "",
        }
        cls.check_transaction_response = {
            "data": {
                "payment_status_code": 0,
                "total_amount": cls.amount,
                "original_amount": cls.amount,
                "refund_amount": 0,
                "discount_amount": 0,
                "payment_amount": cls.amount,
                "payment_currency": cls.currency.name,
                "apv": "544415",
                "payment_status": "APPROVED",
                "transaction_date": "2026-08-03 13:57:20",
            },
            "status": {"code": "00", "message": "Success!", "tran_id": cls.reference},
        }
