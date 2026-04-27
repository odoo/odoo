# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestSubscriptionPaymentIntegration(PaymentHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if cls.env['ir.module.module']._get('payment_demo').state == 'installed':
            cls.demo_provider = cls._prepare_provider(code='demo')

        # having the post process patcher enabled makes the confirmation
        # window close too fast for the tour trigger
        cls.enable_post_process_patcher = False

        cls.sub_propuct_tmpl = cls.env['product.template'].create({
            'name': "Subscription Test Product",
            'type': 'service',
            'list_price': 997.00,
            'recurring_invoice': True,
        })
        cls.sub_product = cls.sub_propuct_tmpl.product_variant_id
        cls.plan_month = cls.env['sale.subscription.plan'].create({
            'name': "Monthly Plan",
            'billing_period_unit': 'month',
        })
        cls.subscription = cls.env['sale.order'].create({
            'name': "Demo Subscription",
            'partner_id': cls.partner.id,
            'plan_id': cls.plan_month.id,
            'order_line': [Command.create({
                'product_id': cls.sub_product.id,
            })],
        })
        cls.subscription.action_confirm()
        cls.invoice = cls.subscription._create_invoices()
        cls.invoice.action_post()

    def create_demo_payment_token(self):
        return self._create_token(
            provider_id=self.demo_provider.id,
            payment_method_id=self.demo_provider.payment_method_ids.id,
            demo_simulated_state='done',
        )

    def start_subscription_invoice_tour(self, tour, invoice=None, login=False, **kwargs):
        self.start_tour((invoice or self.invoice)._get_share_url(), tour, login=login, **kwargs)

    def assertInvoicePaid(self, invoice):
        self.assertIn(invoice.payment_state, {'in_payment', 'paid'}, "Payment should register")
        self.assertAlmostEqual(invoice.amount_paid, invoice.amount_total, "Amount should match")

    def test_subscription_invoice_payment(self):
        """
        Flow:
          - Share the portal link;
          - pay without logging in.
        """
        if self.env['ir.module.module']._get('payment_demo').state != 'installed':
            self.skipTest("payment_demo not found")

        self.start_subscription_invoice_tour('test_subscription_invoice_payment')

        self.assertInvoicePaid(self.invoice)
        self.assertFalse(self.subscription.payment_token_id, "Payment token shouldn't be saved")

    def test_subscription_invoice_tokenize(self):
        """
        Flow:
          - Share the portal link;
          - save payment method without logging in.
        """
        if self.env['ir.module.module']._get('payment_demo').state != 'installed':
            self.skipTest("payment_demo not found")

        self.assertFalse(self.partner.payment_token_ids)
        self.start_subscription_invoice_tour('test_subscription_invoice_tokenize')

        self.assertInvoicePaid(self.invoice)
        self.assertEqual(self.partner.payment_token_count, 1, "Payment token should be saved")
        self.assertFalse(self.subscription.payment_token_id, "Subscription shouln't link to token")

    def test_subscription_invoice_automate(self):
        """
        Flow:
          - Share the portal link;
          - automate payment without logging in.
        """
        if self.env['ir.module.module']._get('payment_demo').state != 'installed':
            self.skipTest("payment_demo not found")

        self.start_subscription_invoice_tour('test_subscription_invoice_automate')

        self.assertInvoicePaid(self.invoice)
        self.assertTrue(self.subscription.payment_token_id, "Payment token should be saved")

    def test_subscription_invoice_tokenized_payment(self):
        """
        Flow:
          - Share the portal link;
          - pay with saved token without logging in.
        """
        if self.env['ir.module.module']._get('payment_demo').state != 'installed':
            self.skipTest("payment_demo not found")

        self.create_demo_payment_token()
        self.start_subscription_invoice_tour('test_subscription_invoice_tokenized_payment')

        self.assertInvoicePaid(self.invoice)
        self.assertFalse(self.subscription.payment_token_id, "Subscription shouln't link to token")

    def test_subscription_invoice_tokenized_automate(self):
        """
        Flow:
          - Share the portal link;
          - automate payment with saved token without logging in.
        """
        if self.env['ir.module.module']._get('payment_demo').state != 'installed':
            self.skipTest("payment_demo not found")

        payment_token = self.create_demo_payment_token()
        self.start_subscription_invoice_tour('test_subscription_invoice_tokenized_automate')

        self.assertInvoicePaid(self.invoice)
        self.assertEqual(
            self.subscription.payment_token_id,
            payment_token,
            "Subscription should be linked to payment token",
        )
