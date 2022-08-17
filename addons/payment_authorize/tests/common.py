# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class AuthorizeCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.authorize = cls._prepare_provider('authorize', update_values={
            'authorize_login': 'dummy',
            'authorize_transaction_key': 'dummy',
            'authorize_signature_key': '00000000',
            'authorize_currency_id': cls.currency_usd.id,
        })

        cls.provider = cls.authorize
        cls.currency = cls.currency_usd
