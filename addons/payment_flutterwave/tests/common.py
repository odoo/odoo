# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class FlutterwaveCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.flutterwave = cls._prepare_provider('flutterwave', update_values={
            'flutterwave_public_key': 'FLWPUBK_TEST-abcdef-X',
            'flutterwave_secret_key': 'FLWSECK_TEST-123456-X',
            'flutterwave_webhook_secret': 'coincoin_motherducker',
        })

        cls.provider = cls.flutterwave

        cls.redirect_payment_data = {
            'status': 'successful',
            'tx_ref': cls.reference,
        }
        cls.webhook_payment_data = {
            'event': 'charge.completed',
            'data': {
                'tx_ref': cls.reference,
            },
        }
        cls.verification_data = {
            'status': 'success',
            'data': {
                'id': '123456789',
                'status': 'successful',
                'card': {
                    'last_4digits': '2950',
                    'token': 'flw-t1nf-f9b3bf384cd30d6fca42b6df9d27bd2f-m03k',
                },
                'customer': {
                    'email': 'user@example.com',
                },
            },
        }
