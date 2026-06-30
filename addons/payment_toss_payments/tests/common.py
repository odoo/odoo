from odoo.addons.payment.tests.common import PaymentCommon


class TossPaymentsCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.toss_payments = cls._prepare_provider(
            'toss_payments',
            update_values={
                'toss_payments_client_key': 'mock-client-key',
                'toss_payments_secret_key': 'mock-secret-key',
            },
        )
        cls.provider = cls.toss_payments

        cls.amount = 750
        cls.currency_krw = cls._enable_currency('KRW')
        cls.currency = cls.currency_krw
        cls.payment_result_data = {
            "orderId": cls.reference,
            "paymentKey": "test-pk",
            "secret": "test-secret",
            "status": "DONE",
            "currency": "KRW",
            "totalAmount": 750,
        }
        cls.webhook_data = {
            "eventType": "PAYMENT_STATUS_CHANGED",
            "data": {
                "orderId": cls.reference,
                "paymentKey": "test-pk",
                "secret": "test-secret",
                "status": "DONE",
                "currency": "KRW",
                "totalAmount": 750,
            },
        }
