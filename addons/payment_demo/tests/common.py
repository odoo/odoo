# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentCommon


class PaymentDemoCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.acquirer = cls._prepare_acquirer(provider='demo')

        cls.notification_data = {
            'reference': cls.reference,
            'payment_details': '1234',
            'simulated_state': 'done',
        }
