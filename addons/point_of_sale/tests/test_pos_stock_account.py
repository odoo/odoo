# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSStock(TestPoSCommon):
    """ Tests for anglo saxon accounting scenario.
    """
    def setUp(self):
        super(TestPoSStock, self).setUp()

        self.config = self.basic_config
        self.product1 = self.create_product('Product 1', self.categ_anglo, 10.0, 5.0)
        self.product2 = self.create_product('Product 2', self.categ_anglo, 20.0, 10.0)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15.0)
        # start inventory with 10 items for each product
        self.adjust_inventory([self.product1, self.product2, self.product3], [10, 10, 10])

        # change cost(standard_price) of anglo products
        # then set inventory from 10 -> 15
        self.product1.write({'standard_price': 6.0})
        self.product2.write({'standard_price': 6.0})
        self.adjust_inventory([self.product1, self.product2, self.product3], [15, 15, 15])

        # change cost(standard_price) of anglo products
        # then set inventory from 15 -> 25
        self.product1.write({'standard_price': 13.0})
        self.product2.write({'standard_price': 13.0})
        self.adjust_inventory([self.product1, self.product2, self.product3], [25, 25, 25])

        self.output_account = self.categ_anglo.property_stock_account_output_categ_id
        self.expense_account = self.categ_anglo.property_account_expense_categ_id
        self.valuation_account = self.categ_anglo.property_stock_valuation_account_id

    def test_01_orders_no_invoiced(self):
        """

        Orders
        ======
        +---------+----------+-----+-------------+------------+
        | order   | product  | qty | total price | total cost |
        +---------+----------+-----+-------------+------------+
        | order 1 | product1 |  10 |       100.0 |       50.0 |  -> 10 items at cost of 5.0 is consumed, remains 5 items at 6.0 and 10 items at 13.0
        |         | product2 |  10 |       200.0 |      100.0 |  -> 10 items at cost of 10.0 is consumed, remains 5 items at 6.0 and 10 items at 13.0
        +---------+----------+-----+-------------+------------+
        | order 2 | product2 |   7 |       140.0 |       56.0 |  -> 5 items at cost of 6.0 and 2 items at cost of 13.0, remains 8 items at cost of 13.0
        |         | product3 |   7 |       210.0 |        0.0 |
        +---------+----------+-----+-------------+------------+
        | order 3 | product1 |   6 |        60.0 |       43.0 |  -> 5 items at cost of 6.0 and 1 item at cost of 13.0, remains 9 items at cost of 13.0
        |         | product2 |   6 |       120.0 |       78.0 |  -> 6 items at cost of 13.0, remains 2 items at cost of 13.0
        |         | product3 |   6 |       180.0 |        0.0 |
        +---------+----------+-----+-------------+------------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        | -1010.0 |
        | pos_receivable-cash |  1010.0 |
        | expense_account     |   327.0 |
        | output_account      |  -327.0 |
        +---------------------+---------+
        | Total balance       |    0.00 |
        +---------------------+---------+
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 10), (self.product2, 10)]))
        orders.append(self.create_ui_order_data([(self.product2, 7), (self.product3, 7)]))
        orders.append(self.create_ui_order_data([(self.product1, 6), (self.product2, 6), (self.product3, 6)]))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')
        self.assertAlmostEqual(orders_total, 1010.0, msg='The orders\'s total amount should equal the computed.')

        # check product qty_available after syncing the order
        self.assertEqual(self.product1.qty_available, 9)
        self.assertEqual(self.product2.qty_available, 2)
        self.assertEqual(self.product3.qty_available, 12)

        # picking and stock moves should be in done state
        for order in self.pos_session.order_ids:
            self.assertEqual(order.picking_ids[0].state, 'done', 'Picking should be in done state.')
            self.assertTrue(all(state == 'done' for state in order.picking_ids[0].move_lines.mapped('state')), 'Move Lines should be in done state.' )

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        account_move = self.pos_session.move_id

        sales_line = account_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sales_line.balance, -orders_total, msg='Sales line balance should be equal to total orders amount.')

        receivable_line_cash = account_move.line_ids.filtered(lambda line: line.account_id in self.pos_receivable_account + self.env['account.account'].search([('name', '=', 'Account Receivable (PoS)')]) and self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 1010.0, msg='Cash receivable should be equal to the total cash payments.')

        expense_line = account_move.line_ids.filtered(lambda line: line.account_id == self.expense_account)
        self.assertAlmostEqual(expense_line.balance, 327.0)

        output_line = account_move.line_ids.filtered(lambda line: line.account_id == self.output_account)
        self.assertAlmostEqual(output_line.balance, -327.0)

        self.assertTrue(receivable_line_cash.full_reconcile_id, msg='Cash receivable line should be fully-reconciled.')
        self.assertTrue(output_line.full_reconcile_id, msg='The stock output account line should be fully-reconciled.')

    def test_02_orders_with_invoice(self):
        """

        Orders
        ======
        Same with test_01 but order 3 is invoiced.

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        |  -650.0 |
        | pos_receivable-cash |  1010.0 |
        | receivable          |  -360.0 |
        | expense_account     |   206.0 |
        | output_account      |  -206.0 |
        +---------------------+---------+
        | Total balance       |    0.00 |
        +---------------------+---------+
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 10), (self.product2, 10)]))
        orders.append(self.create_ui_order_data([(self.product2, 7), (self.product3, 7)]))
        invoiced_uid = self.create_random_uid()
        orders.append(self.create_ui_order_data(
            [(self.product1, 6), (self.product2, 6), (self.product3, 6)],
            is_invoiced=True,
            customer=self.customer,
            uid=invoiced_uid,
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')
        self.assertAlmostEqual(orders_total, 1010.0, msg='The orders\'s total amount should equal the computed.')

        # check product qty_available after syncing the order
        self.assertEqual(self.product1.qty_available, 9)
        self.assertEqual(self.product2.qty_available, 2)
        self.assertEqual(self.product3.qty_available, 12)

        # picking and stock moves should be in done state
        for order in self.pos_session.order_ids:
            self.assertEqual(order.picking_ids[0].state, 'done', 'Picking should be in done state.')
            self.assertTrue(all(state == 'done' for state in order.picking_ids[0].move_lines.mapped('state')), 'Move Lines should be in done state.' )

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        account_move = self.pos_session.move_id

        sales_line = account_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sales_line.balance, -650.0)

        receivable_line = account_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertAlmostEqual(receivable_line.balance, -360.0, msg='Receivable line balance should equal the negative of total amount of invoiced orders.')

        receivable_line_cash = account_move.line_ids.filtered(lambda line: line.account_id in self.pos_receivable_account + self.env['account.account'].search([('name', '=', 'Account Receivable (PoS)')]) and self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 1010.0, msg='Cash receivable should be equal to the total cash payments.')

        expense_line = account_move.line_ids.filtered(lambda line: line.account_id == self.expense_account)
        self.assertAlmostEqual(expense_line.balance, 206.0)

        output_line = account_move.line_ids.filtered(lambda line: line.account_id == self.output_account)
        self.assertAlmostEqual(output_line.balance, -206.0)

        # check order journal entry
        invoiced_order = self.pos_session.order_ids.filtered(lambda order: invoiced_uid in order.pos_reference)
        invoiced_output_account_lines = invoiced_order.account_move.line_ids.filtered(lambda line: line.account_id == self.output_account)
        self.assertAlmostEqual(sum(invoiced_output_account_lines.mapped('balance')), -121.0)

        # The stock output account move lines of the invoiced order should be properly reconciled
        for move_line in invoiced_order.account_move.line_ids.filtered(lambda line: line.account_id == self.output_account):
            self.assertTrue(move_line.full_reconcile_id)

        self.assertTrue(receivable_line_cash.full_reconcile_id, msg='Cash receivable line should be fully-reconciled.')
        self.assertTrue(output_line.full_reconcile_id, msg='The stock output account line should be fully-reconciled.')
