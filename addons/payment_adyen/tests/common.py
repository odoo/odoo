# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class AdyenCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.adyen = cls._prepare_acquirer('adyen', update_values={
            'adyen_merchant_account': 'dummy',
            'adyen_api_key': 'dummy',
            'adyen_hmac_key': 'dummy',
            'adyen_checkout_api_url': 'https://this.is.an.url',
            'adyen_recurring_api_url': 'https://this.is.an.url',
        })

        # Override default values
        cls.acquirer = cls.adyen
