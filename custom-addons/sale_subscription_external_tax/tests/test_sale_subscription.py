# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
from unittest.mock import patch

from odoo.tests.common import tagged
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


class TestSaleSubscriptionExternalCommon:
    @contextmanager
    def patch_set_external_taxes(self):
        def is_computed_externally(self):
            for move in self.filtered(lambda record: record._name == 'account.move'):
                move.is_tax_computed_externally = move.move_type == 'out_invoice'

            for order in self.filtered(lambda record: record._name == 'sale.order'):
                order.is_tax_computed_externally = True

        # autospec to capture self in call_args_list (https://docs.python.org/3/library/unittest.mock-examples.html#mocking-unbound-methods)
        # patch out the _post because _create_recurring_invoice will auto-post the invoice which will also trigger tax computation, that's not what this test is about
        with patch('odoo.addons.account_external_tax.models.account_move.AccountMove._set_external_taxes', autospec=True) as mocked_set, \
             patch('odoo.addons.account_external_tax.models.account_move.AccountMove._post', lambda self, *args, **kwargs: self), \
             patch('odoo.addons.account_external_tax.models.account_external_tax_mixin.AccountExternalTaxMixin._compute_is_tax_computed_externally', is_computed_externally):
            yield mocked_set

    @contextmanager
    def patch_set_external_taxes_so(self, new_sale_set_external_taxes):
        with patch('odoo.addons.sale_external_tax.models.sale_order.SaleOrder._set_external_taxes', new_sale_set_external_taxes):
            yield


@tagged("-at_install", "post_install")
class TestSaleSubscriptionExternal(TestSubscriptionCommon, TestSaleSubscriptionExternalCommon):
    def test_01_subscription_external_taxes_called(self):
        self.subscription.action_confirm()

        with self.patch_set_external_taxes() as mocked_set:
            invoice = self.subscription.with_context(auto_commit=False)._create_recurring_invoice()

        self.assertIn(
            invoice,
            [args[0] for args, kwargs in mocked_set.call_args_list],
            'Should have queried external taxes on the new invoice.'
        )

    def test_02_subscription_do_payment(self):
        invoice_values = self.subscription._prepare_invoice()
        new_invoice = self.env["account.move"].create(invoice_values)

        payment_method = self.env['payment.token'].create({
            'payment_details': 'Jimmy McNulty',
            'partner_id': self.subscription.partner_id.id,
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method_id,
            'provider_ref': 'Omar Little'
        })

        with self.patch_set_external_taxes() as mocked_set:
            self.subscription._do_payment(payment_method, new_invoice)

        self.assertIn(
            new_invoice,
            [args[0] for args, kwargs in mocked_set.call_args_list],
            'Should have queried external taxes on the new invoice.'
        )

    def test_03_subscription_fully_paid(self):
        sub = self.subscription
        self.assertGreater(sub.amount_tax, 0, 'Subscription should have taxes so this test can test what happens when Avatax overrides it.')

        def new_set_external_taxes(self, mapped_taxes, summary):
            """Simulate what happens for an exempt sale order: amounts that don't match the set tax."""
            sub.amount_total = 21.00
            sub.amount_tax = 0.00

        # Calculate initial taxes
        with self.patch_set_external_taxes(), self.patch_set_external_taxes_so(new_set_external_taxes):
            sub.button_external_tax_calculation()

        tx = self.env['payment.transaction'].sudo().create({
            'payment_method_id': self.payment_method_id,
            'amount': sub.amount_total,
            'currency_id': sub.currency_id.id,
            'provider_id': self.provider.id,
            'reference': 'test',
            'operation': 'online_redirect',
            'partner_id': self.partner.id,
            'sale_order_ids': sub.ids,
            'state': 'done',
        })
        self.provider.journal_id.inbound_payment_method_line_ids |= self.env["account.payment.method.line"].sudo().create({
            'payment_method_id': self.env["account.payment.method"].sudo().create({
                'name': 'test',
                'payment_type': 'inbound',
                'code': 'none',
            }).id,
        })

        with self.patch_set_external_taxes(), self.patch_set_external_taxes_so(new_set_external_taxes):
            tx._reconcile_after_done()

        self.assertTrue(sub._is_paid(), 'Subscription should be fully paid')
