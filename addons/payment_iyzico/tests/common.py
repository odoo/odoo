# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class IyzicoCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.iyzico = cls._prepare_provider('iyzico', update_values={
            'iyzico_key_id': 'iyzipay_key',
            'iyzico_key_secret': 'iyzipay_secret',
        })
        cls.provider = cls.iyzico
        cls.return_data = {
            'token': 'dummy_token',
        }
        cls.signature = 'abc_xyz'
        cls.payment_data = {
            'conversationId': cls.reference,
            'paymentId': '24232079',
            'paidPrice': cls.amount,
            'paymentStatus': 'SUCCESS',
            'token': 'dummy_token',
        }
        cls.webhook_data = {
            **cls.payment_data,
            'paymentConversationId': cls.reference,
        }
