# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class StripeCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.stripe = cls._prepare_acquirer('stripe', update_values={
            'stripe_secret_key': 'sk_test_KJtHgNwt2KS3xM7QJPr4O5E8',
            'stripe_publishable_key': 'pk_test_QSPnimmb4ZhtkEy3Uhdm4S6J',
            'stripe_webhook_secret': 'whsec_vG1fL6CMUouQ7cObF2VJprLVXT5jBLxB',
            'payment_icon_ids': [(5, 0, 0)],
        })

        cls.acquirer = cls.stripe
