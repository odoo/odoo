from odoo.addons.payment.tests.common import PaymentCommon


class XenditCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.xendit = cls._prepare_provider('xendit', update_values={
            'xendit_api_key': 'xnd_development_zcJ0sLkfgv5mZ6G8hByIJxlhk6yfKDQgWYRSXY3bquGVdMpne7k7KL7QJhr2xk',
            'xendit_webhook_token': 'sYFoR4IJxz680OCSjF6B3NAPVQUGVBFRQpYdqwcx0hgIPgYJ',
        })

        cls.provider = cls.xendit
        cls.redirect_notification_data = {
            'Ref': cls.reference,
        }
        cls.webhook_notification_data_invoice = {
            "amount": 1740,
            "status": "PAID",
            "created": "2023-07-12T09:31:13.111Z",
            "paid_at": "2023-07-12T09:31:22.830Z",
            "updated": "2023-07-12T09:31:23.577Z",
            "user_id": "64118d86854d7d89206e732d",
            "currency": "IDR",
            "bank_code": "BNI",
            "description": "TEST0001",
            "external_id": "TEST0001",
            "paid_amount": 1740,
            "merchant_name": "Odoo",
            "initial_amount": 1740,
            "payment_method": "BANK_TRANSFER",
            "payment_channel": "BNI",
            "payment_destination": "880891384013",
        }
        cls.webhook_notification_data_invoice_cc = {
            "id": "64dee1ac17789072a2c51667",
            "amount": 1443000,
            "status": "PAID",
            "created": "2023-08-18T03:12:45.356Z",
            "is_high": False,
            "paid_at": "2023-08-18T03:13:11.542Z",
            "updated": "2023-08-18T03:13:14.762Z",
            "user_id": "64118d86854d7d89206e732d",
            "currency": "IDR",
            "description": "S00003",
            "external_id": "TEST0002",
            "paid_amount": 1443000,
            "merchant_name": "Odoo",
            "payment_method": "CREDIT_CARD",
            "payment_channel": "CREDIT_CARD",
            "credit_card_token": "64ded2285d2ee30019dd456a",
            "failure_redirect_url": "http://localhost:8069/payment/status",
            "success_redirect_url": "http://localhost:8069/payment/status",
            "credit_card_charge_id": "64dee1c75d2ee30019dd4841"
        }
        cls.webhook_notification_data_refund = {
            "created": "2023-08-17T02:34:27.009Z",
            "business_id": "64118d86854d7d89206e732d",
            "event": "refund.succeeded",
            "data": {
                "id": "RFD-00001",
                "amount": 1110000,
                "reason": "OTHERS",
                "status": "SUCCEEDED",
                "country": "ID",
                "created": "2023-08-17T02:34:24.963128Z",
                "updated": "2023-08-17T02:34:24.963128Z",
                "currency": "IDR",
                "invoice_id": "64dc9fc9a23a9340d20c309d",
                "payment_id": "ewc_b4eab1df-139f-4c96-9fb4-ec492f589895",
                "channel_code": "DANA",
                "reference_id": "",
                "refund_method": "DIRECT",
                "payment_method_type": "EWALLET",
            },
        }
