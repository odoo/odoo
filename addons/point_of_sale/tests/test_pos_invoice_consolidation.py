# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import tagged
from odoo.addons.point_of_sale.tests.common import CommonPosTest


# TODO-PARP: Move tests and remove File

@tagged('post_install', '-at_install')
class TestPosInvoiceConsolidation(CommonPosTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.pos_config_usd
        cls.user1 = cls.env.user
        cls.user2 = cls.simple_accountman
        cls.user2.group_ids = [Command.link(cls.env.ref('point_of_sale.group_pos_user').id)]
        cls.product1 = cls.create_product('Product 1', cls.categ_basic, 10.0)
        cls.product2 = cls.create_product('Product 2', cls.categ_basic, 20.0)

    def _consolidate(self, orders):
        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=orders.ids).action_create_invoices()

    def test_ignore_generated_invoices(self):
        self.open_new_session()

        with self.with_user(self.user1.login):
            orders_user1 = self.create_orders([{
                'lines': [(self.product1, 1)],
                'customer': self.customer,
                'to_invoice': False,
                'uuid': 'u1-order',
            }])
            # This flattens the dict into the recordset
            orders_user1 = sum(orders_user1.values(), self.env['pos.order'])

        with self.with_user(self.user2.login):
            orders_user2 = self.create_orders([
                {
                    'lines': [(self.product1, 2)],
                    'customer': self.customer,
                    'to_invoice': False,
                }, {
                    'lines': [(self.product2, 1)],
                    'customer': self.customer,
                    'to_invoice': False,
                }
            ])
            # This flattens the dict into the recordset
            orders_user2 = sum(orders_user2.values(), self.env['pos.order'])

        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=orders_user1.ids).action_create_invoices()

        invoice_user1 = orders_user1.account_move
        invoice_user2 = orders_user2.account_move

        self.assertEqual(len(invoice_user1), 1, "User 1 should have one invoice")
        self.assertEqual(orders_user1.amount_total, invoice_user1.amount_total)

        self.assertEqual(len(invoice_user2), 0, "User 2 should have no invoices")

        all_orders = orders_user1 + orders_user2
        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=all_orders.ids).action_create_invoices()
        invoice_user1 = orders_user1.account_move
        invoice_user2 = orders_user2.account_move

        self.assertEqual(len(invoice_user1), 1, "User 1 should have one invoice")
        self.assertEqual(orders_user1.amount_total, invoice_user1.amount_total)

        self.assertEqual(len(invoice_user2), 1, "User 2 should have one invoice")
        self.assertEqual(sum(orders_user2.mapped('amount_total')), invoice_user2.amount_total)

    def test_invoice_grouped_by_user_id(self):
        self.open_new_session()

        with self.with_user(self.user1.login):
            orders_user1 = self.create_orders([{
                'lines': [(self.product1, 1)],
                'customer': self.customer,
                'to_invoice': False,
                'uuid': 'u1-order',
            }])
            # This flattens the dict into the recordset
            orders_user1 = sum(orders_user1.values(), self.env['pos.order'])

        with self.with_user(self.user2.login):
            orders_user2 = self.create_orders([
                {
                    'lines': [(self.product1, 2)],
                    'customer': self.customer,
                    'to_invoice': False,
                }, {
                    'lines': [(self.product2, 1)],
                    'customer': self.customer,
                    'to_invoice': False,
                }
            ])
            # This flattens the dict into the recordset
            orders_user2 = sum(orders_user2.values(), self.env['pos.order'])

        all_orders = orders_user1 + orders_user2

        # create consolidated invoice
        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=all_orders.ids).action_create_invoices()

        invoice_user1 = orders_user1.account_move
        invoice_user2 = orders_user2.account_move

        self.assertEqual(len(invoice_user1), 1, "User 1 should have one invoice")
        self.assertEqual(orders_user1.amount_total, invoice_user1.amount_total)

        self.assertEqual(len(invoice_user2), 1, "User 2 should have one invoice")
        self.assertEqual(sum(orders_user2.mapped('amount_total')), invoice_user2.amount_total)

    def test_consolidation_with_refund(self):
        """ A refund consolidated with sales that outweigh it must give a customer invoice of the net amount. """
        self.open_new_session()

        with self.with_user(self.user1.login):
            orders = self.create_orders([
                {'lines': [(self.product1, 1)], 'customer': self.customer, 'to_invoice': False, 'uuid': 'sale-1'},
                {'lines': [(self.product2, 1)], 'customer': self.customer, 'to_invoice': False, 'uuid': 'sale-2'},
            ])
            refund = self.refund_pos_order(orders['sale-1'], self.cash_pm, -orders['sale-1'].amount_total)

        self.close_pos_session()

        all_orders = orders['sale-1'] | orders['sale-2'] | refund
        self._consolidate(all_orders)

        invoice = all_orders.account_move
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.amount_total, 20.0)

    def test_consolidation_with_refund_outweighing_sales(self):
        """ When the refunds outweigh the sales, the consolidated document is a credit note. """
        self.open_new_session()

        with self.with_user(self.user1.login):
            orders = self.create_orders([
                {'lines': [(self.product2, 1)], 'customer': self.customer, 'to_invoice': False, 'uuid': 'sale-1'},
                {'lines': [(self.product1, 1)], 'customer': self.customer, 'to_invoice': False, 'uuid': 'sale-2'},
            ])
            refund = self.refund_pos_order(orders['sale-1'], self.cash_pm, -orders['sale-1'].amount_total)

        self.close_pos_session()

        # sale-1 is left out of the selection, so the refund outweighs the sale: 10 - 20 = -10
        selected_orders = orders['sale-2'] | refund
        self._consolidate(selected_orders)

        invoice = selected_orders.account_move
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, 'out_refund')
        self.assertEqual(invoice.amount_total, 10.0)

    def test_consolidation_with_refund_and_cash_rounding(self):
        """ Same as test_consolidation_with_refund, but with a cash rounding method on the config. """
        self.open_new_session()

        income_acc = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
        expense_acc = self.env['account.account'].search([('account_type', '=', 'expense')], limit=1)
        rounding = self.env['account.cash.rounding'].create({
            'name': 'Rounding 0.05',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': income_acc.id,
            'loss_account_id': expense_acc.id,
        })
        self.config.write({
            'cash_rounding': True,
            'only_round_cash_method': False,
            'rounding_method': rounding.id,
        })

        with self.with_user(self.user1.login):
            orders = self.create_orders([
                {'lines': [(self.product1, 1)], 'customer': self.customer, 'to_invoice': False, 'uuid': 'sale-1'},
                {'lines': [(self.product2, 1)], 'customer': self.customer, 'to_invoice': False, 'uuid': 'sale-2'},
            ])
            refund = self.refund_pos_order(orders['sale-1'], self.cash_pm, -orders['sale-1'].amount_total)

        self.close_pos_session()

        all_orders = orders['sale-1'] | orders['sale-2'] | refund
        self._consolidate(all_orders)

        invoice = all_orders.account_move
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.amount_total, 20.0)
        rounding_lines = invoice.line_ids.filtered(lambda line: line.display_type == 'rounding')
        self.assertEqual(sum(rounding_lines.mapped('balance')), 0.0, "nothing to round, so no rounding line should compensate anything")

    def test_consolidation_non_cash_with_cash_rounding_enabled(self):
        """Cash rounding enabled, consolidate +/- orders paid non-cash; force delta; no crash."""
        self.open_new_session()

        income_acc = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
        expense_acc = self.env['account.account'].search([('account_type', '=', 'expense')], limit=1)

        rounding = self.env['account.cash.rounding'].create({
            'name': 'Rounding 0.05',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': income_acc.id,
            'loss_account_id': expense_acc.id,
        })

        self.config.write({
            'cash_rounding': True,
            'only_round_cash_method': True,
            'rounding_method': rounding.id,
        })

        non_cash_pm = self.bank_pm
        self.assertTrue(non_cash_pm, "Need at least one non-cash payment method on the POS config.")
        self.product2.lst_price = 9.99
        with self.with_user(self.user1.login):
            orders = self.create_orders([
                {'lines': [(self.product1, 1)], 'customer': self.customer, 'payments': [(non_cash_pm, 10)]},
                {
                    'lines': [(self.product2, 1)],
                    'customer': self.customer,
                    'to_invoice': False,
                    'payments': [(self.cash_pm, 10)]},
            ])
            orders = sum(orders.values(), self.env['pos.order'])

        self.assertEqual(len(orders), 2, "Should have created 2 orders")
        self.assertEqual(orders.mapped('amount_total'), [10.0, 9.99])
        self.assertEqual(orders.mapped('amount_paid'), [10.0, 10.0])
        self.assertEqual(orders.mapped('amount_difference'), [0.0, 0.01])
        self.assertEqual(orders.mapped('amount_return'), [0.0, 0.0])
        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=orders.ids).action_create_invoices()
        self.assertEqual(len(orders.account_move), 1)
