# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.payment.tests.common import PaymentCommon


class AuthorizeCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.authorize = cls._prepare_provider('authorize', update_values={
            'authorize_login': 'dummy',
            'authorize_transaction_key': 'dummy',
            'authorize_signature_key': '00000000',
            'authorize_webhook_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
            'available_currency_ids': [Command.set(cls.currency_usd.ids)]
        })

        cls.provider = cls.authorize
        cls.currency = cls.currency_usd
        cls.trans_id = '60123456789'

        # Base webhook notification structure
        cls.webhook_authcapture_data = {
            'notificationId': 'e4bc2a42-69e7-4cc4-bf0b-00d0c1a34c8e',
            'eventType': 'net.authorize.payment.authcapture.created',
            'eventDate': '2023-10-15T10:30:00.000Z',
            'webhookId': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
            'payload': {
                'responseCode': 1,
                'authCode': '123456',
                'avsResponse': 'Y',
                'authAmount': cls.amount,
                'entityName': 'transaction',
                'id': cls.trans_id,
                'invoiceNumber': cls.reference,
            },
        }
