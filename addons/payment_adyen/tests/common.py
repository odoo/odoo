# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class AdyenCommon(PaymentCommon):

    WEBHOOK_NOTIFICATION_PAYLOAD = {
        'additionalData': {
            'hmacSignature': 'kK6vSQvfWP3AtT2TTK1ePj9e7XPb7bF5jHC7jDWyU5c='
        },
        'amount': {
            'currency': 'USD',
            'value': 999,
        },
        'eventCode': 'AUTHORISATION',
        'merchantAccountCode': 'DuckSACom123',
        'merchantReference': 'Test Transaction',  # Shamefully copy-pasted from payment
        'originalReference': 'FEDCBA9876543210',
        'pspReference': '0123456789ABCDEF',
        'success': 'true',
    }  # Include all keys used in the computation of the signature to the payload
    WEBHOOK_NOTIFICATION_BATCH_DATA = {
        'notificationItems': [
            {
                'NotificationRequestItem': WEBHOOK_NOTIFICATION_PAYLOAD,
            }
        ]
    }

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.adyen = cls._prepare_acquirer('adyen', update_values={
            'adyen_merchant_account': 'dummy',
            'adyen_api_key': 'dummy',
            'adyen_client_key': 'dummy',
            'adyen_hmac_key': '12345678',
            'adyen_checkout_api_url': 'https://this.is.an.url',
            'adyen_recurring_api_url': 'https://this.is.an.url',
        })

        # Override default values
        cls.acquirer = cls.adyen
