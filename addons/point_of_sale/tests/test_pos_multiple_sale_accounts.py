# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo import tools
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSMultipleSaleAccounts(TestPoSCommon):
    """ Test to orders containing products with different sale accounts

    keywords/phrases: Different Income Accounts

    In this test, two sale (income) accounts are involved:
        self.sale_account -> default for products because it is in the category
        self.other_sale_account -> manually set to self.product2
    """

    def setUp(self):
        super(TestPoSMultipleSaleAccounts, self).setUp()

        self.config = self.basic_config
        self.product1 = self.create_product(
            'Product 1',
            self.categ_basic,
            lst_price=10.99,
            standard_price=5.0,
            tax_ids=self.taxes['tax7'].ids,
        )
        self.product2 = self.create_product(
            'Product 2',
            self.categ_basic,
            lst_price=19.99,
            standard_price=10.0,
            tax_ids=self.taxes['tax10'].ids,
            sale_account=self.other_sale_account,
        )
        self.product3 = self.create_product(
            'Product 3',
            self.categ_basic,
            lst_price=30.99,
            standard_price=15.0,
            tax_ids=self.taxes['tax_group_7_10'].ids,
        )
        self.adjust_inventory([self.product1, self.product2, self.product3], [100, 50, 50])

    def test_01_check_product_properties(self):
        self.assertEqual(self.product2.property_account_income_id, self.other_sale_account, 'Income account for the product2 should be the other sale account.')
        self.assertFalse(self.product1.property_account_income_id, msg='Income account for product1 should not be set.')
        self.assertFalse(self.product3.property_account_income_id, msg='Income account for product3 should not be set.')
        self.assertEqual(self.product1.categ_id.property_account_income_categ_id, self.sale_account)
        self.assertEqual(self.product3.categ_id.property_account_income_categ_id, self.sale_account)

    def test_02_orders_without_invoice(self):
        """ orders without invoice

        Orders
        ======
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order   | payments | invoiced? | product  | qty | untaxed | tax                      |  total |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order 1 | cash     | no        | product1 |  10 |   109.9 | 7.69 [7%]                | 117.59 |
        |         |          |           | product2 |  10 |  181.73 | 18.17 [10%]              |  199.9 |
        |         |          |           | product3 |  10 |  281.73 | 19.72 [7%] + 28.17 [10%] | 329.62 |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order 2 | cash     | no        | product1 |   5 |   54.95 | 3.85 [7%]                |  58.80 |
        |         |          |           | product2 |   5 |   90.86 | 9.09 [10%]               |  99.95 |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order 3 | bank     | no        | product2 |   5 |   90.86 | 9.09 [10%]               |  99.95 |
        |         |          |           | product3 |   5 |  140.86 | 9.86 [7%] + 14.09 [10%]  | 164.81 |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        | -164.85 |  (for the 7% base amount)
        | sale_account        | -422.59 |  (for the 7+10% base amount)
        | other_sale_account  | -363.45 |
        | tax 7%              |  -41.12 |
        | tax 10%             |  -78.61 |
        | pos receivable bank |  264.76 |
        | pos receivable cash |  805.86 |
        +---------------------+---------+
        | Total balance       |    0.00 |
        +---------------------+---------+
        """

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 10), (self.product2, 10), (self.product3, 10)]))
        orders.append(self.create_ui_order_data([(self.product1, 5), (self.product2, 5)]))
        orders.append(self.create_ui_order_data([(self.product2, 5), (self.product3, 5)], payments=[(self.bank_pm, 264.76)]))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sale_account_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        for balance, amount in zip(sorted(sale_account_lines.mapped('balance')), sorted([-164.85, -422.59])):
            self.assertAlmostEqual(balance, amount)

        other_sale_account_line = session_move.line_ids.filtered(lambda line: line.account_id == self.other_sale_account)
        self.assertAlmostEqual(other_sale_account_line.balance, -363.45)

        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 264.76)

        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 805.86)

        manually_calculated_taxes = (-41.12, -78.61)
        tax_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)
        self.assertAlmostEqual(sum(manually_calculated_taxes), sum(tax_lines.mapped('balance')))
        for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
            self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined.')

        self.assertTrue(receivable_line_cash.full_reconcile_id)

    def test_03_orders_with_invoice(self):
        """ orders with invoice

        Orders
        ======
        +---------+----------+---------------+----------+-----+---------+--------------------------+--------+
        | order   | payments | invoiced?     | product  | qty | untaxed | tax                      |  total |
        +---------+----------+---------------+----------+-----+---------+--------------------------+--------+
        | order 1 | cash     | no            | product1 |  10 |   109.9 | 7.69 [7%]                | 117.59 |
        |         |          |               | product2 |  10 |  181.73 | 18.17 [10%]              |  199.9 |
        |         |          |               | product3 |  10 |  281.73 | 19.72 [7%] + 28.17 [10%] | 329.62 |
        +---------+----------+---------------+----------+-----+---------+--------------------------+--------+
        | order 2 | bank     | no            | product1 |   5 |   54.95 | 3.85 [7%]                |  58.80 |
        |         |          |               | product2 |   5 |   90.86 | 9.09 [10%]               |  99.95 |
        +---------+----------+---------------+----------+-----+---------+--------------------------+--------+
        | order 3 | bank     | yes, customer | product2 |   5 |   90.86 | 9.09 [10%]               |  99.95 |
        |         |          |               | product3 |   5 |  140.86 | 9.86 [7%] + 14.09 [10%]  | 164.81 |
        +---------+----------+---------------+----------+-----+---------+--------------------------+--------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        | -164.85 |  (for the 7% base amount)
        | sale_account        | -281.73 |  (for the 7+10% base amount)
        | other_sale_account  | -272.59 |
        | tax 7%              |  -31.26 |
        | tax 10%             |  -55.43 |
        | pos receivable cash |  647.11 |
        | pos receivable bank |  423.51 |
        | receivable          | -264.76 |
        +---------------------+---------+
        | Total balance       |    0.00 |
        +---------------------+---------+
        """

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 10), (self.product2, 10), (self.product3, 10)]))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product2, 5)],
            payments=[(self.bank_pm, 158.75)],
        ))
        orders.append(self.create_ui_order_data(
            [(self.product2, 5), (self.product3, 5)],
            payments=[(self.bank_pm, 264.76)],
            customer=self.customer,
            is_invoiced=True,
            uid='09876-098-0987',
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # check if there is one invoiced order
        self.assertEqual(len(self.pos_session.order_ids.filtered(lambda order: order.state == 'invoiced')), 1, 'There should only be one invoiced order.')

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sale_account_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        for balance, amount in zip(sorted(sale_account_lines.mapped('balance')), sorted([-164.85, -281.73])):
            self.assertAlmostEqual(balance, amount)

        other_sale_account_line = session_move.line_ids.filtered(lambda line: line.account_id == self.other_sale_account)
        self.assertAlmostEqual(other_sale_account_line.balance, -272.59)

        pos_receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(pos_receivable_line_bank.balance, 423.51)

        pos_receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(pos_receivable_line_cash.balance, 647.11)

        manually_calculated_taxes = (-31.26, -55.43)
        tax_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)
        self.assertAlmostEqual(sum(manually_calculated_taxes), sum(tax_lines.mapped('balance')))
        for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
            self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined.')

        receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertAlmostEqual(receivable_line.balance, -264.76)

        self.assertTrue(pos_receivable_line_cash.full_reconcile_id)
        self.assertTrue(receivable_line.full_reconcile_id)
