# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class AdyenCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.adyen = cls._prepare_provider('adyen', update_values={
            'adyen_merchant_account': 'dummy',
            'adyen_api_key': 'dummy',
            'adyen_client_key': 'dummy',
            'adyen_hmac_key': '12345678',
            'adyen_checkout_api_url': 'https://this.is.an.url',
            'adyen_recurring_api_url': 'https://this.is.an.url',
        })

        # Override default values
        cls.provider = cls.adyen

        cls.psp_reference = '0123456789ABCDEF'
        cls.original_reference = 'FEDCBA9876543210'
        cls.webhook_notification_payload = {
            'additionalData': {
                'hmacSignature': 'kK6vSQvfWP3AtT2TTK1ePj9e7XPb7bF5jHC7jDWyU5c='
            },
            'amount': {
                'currency': 'USD',
                'value': 999,
            },
            'eventCode': 'AUTHORISATION',
            'merchantAccountCode': 'DuckSACom123',
            'merchantReference': cls.reference,
            'originalReference': cls.original_reference,
            'pspReference': cls.psp_reference,
            'success': 'true',
        }  # Include all keys used in the computation of the signature to the payload
        cls.webhook_notification_batch_data = {
            'notificationItems': [
                {
                    'NotificationRequestItem': cls.webhook_notification_payload,
                }
            ]
        }

    def _create_transaction(self, *args, provider_reference=None, **kwargs):
        if not provider_reference:
            provider_reference = self.psp_reference
        return super()._create_transaction(*args, provider_reference=provider_reference, **kwargs)
