# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class XenditCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.xendit = cls._prepare_provider('xendit', update_values={
            'xendit_secret_key': 'xnd_secret_key',
            'xendit_webhook_token': 'xnd_webhook_token',
        })
        cls.provider = cls.xendit
        cls.webhook_notification_data = {
            'amount': 1740,
            'status': 'PAID',
            'created': '2023-07-12T09:31:13.111Z',
            'paid_at': '2023-07-12T09:31:22.830Z',
            'updated': '2023-07-12T09:31:23.577Z',
            'user_id': '64118d86854d7d89206e732d',
            'currency': 'IDR',
            'bank_code': 'BNI',
            'description': cls.reference,
            'external_id': cls.reference,
            'paid_amount': 1740,
            'merchant_name': 'Odoo',
            'initial_amount': 1740,
            'payment_method': 'BANK_TRANSFER',
            'payment_channel': 'BNI',
            'payment_destination': '880891384013',
        }
