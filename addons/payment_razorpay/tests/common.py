# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class RazorpayCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.provider = cls._prepare_provider('razorpay', update_values={
            'razorpay_key_id': 'rzp_123',
            'razorpay_key_secret': 'Y63AyP9eL91',
            'razorpay_webhook_secret': 'coincoin_motherducker',
        })

        cls.payment_id = 'pay_123'
        cls.refund_id = 'rfd_456'
        cls.order_id = 'order_789'
        cls.redirect_notification_data = {
            'razorpay_payment_id': cls.payment_id,
            'razorpay_order_id': cls.order_id,
            'razorpay_signature': 'dummy',
        }
        cls.payment_data = {
            'id': cls.payment_id,
            'description': cls.reference,
            'status': 'captured',
        }
        cls.refund_data = {
            'id': cls.refund_id,
            'payment_id': cls.payment_id,
            'amount': cls.amount,
        }
        cls.webhook_notification_data = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': cls.payment_data,
                },
            },
        }
