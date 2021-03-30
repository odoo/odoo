# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class PayulatamCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.payulatam = cls._prepare_acquirer('payulatam', update_values={
            'payulatam_account_id': 'dummy',
            'payulatam_merchant_id': 'dummy',
            'payulatam_api_key': 'dummy',
        })

        # Override default values
        cls.acquirer = cls.payulatam
        cls.currency = cls.currency_euro
