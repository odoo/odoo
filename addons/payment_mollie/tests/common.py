# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class MollieCommon(PaymentCommon):

    NOTIFICATION_DATA = {
        'ref': 'Test Transaction',  # Shamefully copy-pasted from payment
        'id': 'tr_ABCxyz0123',
    }

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.mollie = cls._prepare_acquirer('mollie', update_values={
            'mollie_api_key': 'dummy',
        })
        cls.acquirer = cls.mollie
        cls.currency = cls.currency_euro
