# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class OgoneCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.ogone = cls._prepare_acquirer('ogone', update_values={
            'ogone_pspid': 'dummy',
            'ogone_userid': 'dummy',
            'ogone_password': 'dummy',
            'ogone_shakey_in': 'dummy',
            'ogone_shakey_out': 'dummy',
        })

        cls.acquirer = cls.ogone
        cls.currency = cls.currency_euro
