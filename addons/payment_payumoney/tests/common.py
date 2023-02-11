# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class PayumoneyCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.payumoney = cls._prepare_acquirer('payumoney', update_values={
            'payumoney_merchant_key': 'dummy',
            'payumoney_merchant_salt': 'dummy',
        })

        # Override default values
        cls.acquirer = cls.payumoney
        cls.currency = cls._prepare_currency('INR')
