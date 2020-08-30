# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo import tools
from odoo.tests.common import Form
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSOtherCurrencyConfig(TestPoSCommon):
    """ Test PoS with basic configuration
    """

    def setUp(self):
        super(TestPoSOtherCurrencyConfig, self).setUp()

        self.config = self.other_currency_config
        self.product1 = self.create_product('Product 1', self.categ_basic, 10.0, 5)
        self.product2 = self.create_product('Product 2', self.categ_basic, 20.0, 10)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15)
        self.product4 = self.create_product('Product 4', self.categ_anglo, 100, 50)
        self.product5 = self.create_product('Product 5', self.categ_anglo, 200, 70)
        self.product6 = self.create_product('Product 6', self.categ_anglo, 45.3, 10.73)
        self.product7 = self.create_product('Product 7', self.categ_basic, 7, 7, tax_ids=self.taxes['tax7'].ids)
        self.adjust_inventory(
            [self.product1, self.product2, self.product3, self.product4, self.product5, self.product6, self.product7],
            [100, 50, 50, 100, 100, 100, 100]
        )
        # change the price of product2 to 12.99 fixed. No need to convert.
        pricelist_item = self.env['product.pricelist.item'].create({
            'product_tmpl_id': self.product2.product_tmpl_id.id,
            'fixed_price': 12.99,
        })
        self.config.pricelist_id.write({'item_ids': [(6, 0, (self.config.pricelist_id.item_ids | pricelist_item).ids)]})

        self.output_account = self.categ_anglo.property_stock_account_output_categ_id
        self.expense_account = self.categ_anglo.property_account_expense_categ_id

    def test_01_check_product_cost(self):
        # Product price should be half of the original price because currency rate is 0.5.
        # (see `self._create_other_currency_config` method)
        # Except for product2 where the price is specified in the pricelist.

        self.assertAlmostEqual(self.config.pricelist_id.get_product_price(self.product1, 1, self.customer), 5.00)
        self.assertAlmostEqual(self.config.pricelist_id.get_product_price(self.product2, 1, self.customer), 12.99)
        self.assertAlmostEqual(self.config.pricelist_id.get_product_price(self.product3, 1, self.customer), 15.00)
        self.assertAlmostEqual(self.config.pricelist_id.get_product_price(self.product4, 1, self.customer), 50)
        self.assertAlmostEqual(self.config.pricelist_id.get_product_price(self.product5, 1, self.customer), 100)
        self.assertAlmostEqual(self.config.pricelist_id.get_product_price(self.product6, 1, self.customer), 22.65)
        self.assertAlmostEqual(self.config.pricelist_id.get_product_price(self.product7, 1, self.customer), 3.50)

    def test_02_orders_without_invoice(self):
        """ orders without invoice

        Orders
        ======
        +---------+----------+-----------+----------+-----+-------+
        | order   | payments | invoiced? | product  | qty | total |
        +---------+----------+-----------+----------+-----+-------+
        | order 1 | cash     | no        | product1 |  10 |    50 |
        |         |          |           | product2 |  10 | 129.9 |
        |         |          |           | product3 |  10 |   150 |
        +---------+----------+-----------+----------+-----+-------+
        | order 2 | cash     | no        | product1 |   5 |    25 |
        |         |          |           | product2 |   5 | 64.95 |
        +---------+----------+-----------+----------+-----+-------+
        | order 3 | bank     | no        | product2 |   5 | 64.95 |
        |         |          |           | product3 |   5 |    75 |
        +---------+----------+-----------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+-----------------+
        | account             | balance | amount_currency |
        +---------------------+---------+-----------------+
        | sale_account        | -1119.6 |         -559.80 |
        | pos receivable bank |   279.9 |          139.95 |
        | pos receivable cash |   839.7 |          419.85 |
        +---------------------+---------+-----------------+
        | Total balance       |     0.0 |            0.00 |
        +---------------------+---------+-----------------+
        """

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 10), (self.product2, 10), (self.product3, 10)]))
        orders.append(self.create_ui_order_data([(self.product1, 5), (self.product2, 5)]))
        orders.append(self.create_ui_order_data([(self.product2, 5), (self.product3, 5)], payments=[(self.bank_pm, 139.95)]))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # close the session
        self.pos_session.action_pos_session_validate()
        session_move = self.pos_session.move_id

        sale_account_line = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sale_account_line.balance, -1119.6)
        self.assertAlmostEqual(sale_account_line.amount_currency, -559.80)

        pos_receivable_line_bank = session_move.line_ids.filtered(lambda line: line.account_id == self.pos_receivable_account and self.bank_pm.name in line.name)
        self.assertAlmostEqual(pos_receivable_line_bank.balance, 279.9)
        self.assertAlmostEqual(pos_receivable_line_bank.amount_currency, 139.95)

        pos_receivable_line_cash = session_move.line_ids.filtered(lambda line: line.account_id == self.pos_receivable_account and self.cash_pm.name in line.name)
        self.assertAlmostEqual(pos_receivable_line_cash.balance, 839.7)
        self.assertAlmostEqual(pos_receivable_line_cash.amount_currency, 419.85)

    def test_03_orders_with_invoice(self):
        """ orders with invoice

        Orders
        ======
        +---------+----------+---------------+----------+-----+-------+
        | order   | payments | invoiced?     | product  | qty | total |
        +---------+----------+---------------+----------+-----+-------+
        | order 1 | cash     | no            | product1 |  10 |    50 |
        |         |          |               | product2 |  10 | 129.9 |
        |         |          |               | product3 |  10 |   150 |
        +---------+----------+---------------+----------+-----+-------+
        | order 2 | cash     | yes, customer | product1 |   5 |    25 |
        |         |          |               | product2 |   5 | 64.95 |
        +---------+----------+---------------+----------+-----+-------+
        | order 3 | bank     | yes, customer | product2 |   5 | 64.95 |
        |         |          |               | product3 |   5 |    75 |
        +---------+----------+---------------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+-----------------+
        | account             | balance | amount_currency |
        +---------------------+---------+-----------------+
        | sale_account        |  -659.8 |         -329.90 |
        | pos receivable bank |   279.9 |          139.95 |
        | pos receivable cash |   839.7 |          419.85 |
        | invoice receivable  |  -459.8 |         -229.90 |
        +---------------------+---------+-----------------+
        | Total balance       |     0.0 |            0.00 |
        +---------------------+---------+-----------------+
        """

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 10), (self.product2, 10), (self.product3, 10)]))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product2, 5)],
            customer=self.customer,
            is_invoiced=True,
        ))
        orders.append(self.create_ui_order_data(
            [(self.product2, 5), (self.product3, 5)],
            payments=[(self.bank_pm, 139.95)],
            customer=self.customer,
            is_invoiced=True,
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # close the session
        self.pos_session.action_pos_session_validate()
        session_move = self.pos_session.move_id

        sale_account_line = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sale_account_line.balance, -659.8)
        self.assertAlmostEqual(sale_account_line.amount_currency, -329.9)

        pos_receivable_line_bank = session_move.line_ids.filtered(lambda line: line.account_id == self.pos_receivable_account and self.bank_pm.name in line.name)
        self.assertAlmostEqual(pos_receivable_line_bank.balance, 279.9)
        self.assertAlmostEqual(pos_receivable_line_bank.amount_currency, 139.95)

        pos_receivable_line_cash = session_move.line_ids.filtered(lambda line: line.account_id == self.pos_receivable_account and self.cash_pm.name in line.name)
        self.assertAlmostEqual(pos_receivable_line_cash.balance, 839.7)
        self.assertAlmostEqual(pos_receivable_line_cash.amount_currency, 419.85)

        invoice_receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertAlmostEqual(invoice_receivable_line.balance, -459.8)
        self.assertAlmostEqual(invoice_receivable_line.amount_currency, -229.9)

    def test_04_anglo_saxon_products(self):
        """
        ======
        Orders
        ======
        +---------+----------+-----------+----------+-----+----------+------------+
        | order   | payments | invoiced? | product  | qty |    total | total cost |
        |         |          |           |          |     |          |            |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 1 | cash     | no        | product4 |   7 |      700 |        350 |
        |         |          |           | product5 |   7 |     1400 |        490 |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 2 | cash     | no        | product5 |   6 |     1200 |        420 |
        |         |          |           | product4 |   6 |      600 |        300 |
        |         |          |           | product6 |  49 |   2219.7 |     525.77 |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 3 | cash     | no        | product5 |   2 |      400 |        140 |
        |         |          |           | product6 |  13 |    588.9 |     139.49 |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 4 | cash     | no        | product6 |   1 |     45.3 |      10.73 |
        +---------+----------+-----------+----------+-----+----------+------------+

        ===============
        Expected Result
        ===============
        +---------------------+------------+-----------------+
        | account             |    balance | amount_currency |
        +---------------------+------------+-----------------+
        | sale_account        |   -7153.90 |        -3576.95 |
        | pos_receivable-cash |    7153.90 |         3576.95 |
        | expense_account     |    2375.99 |         2375.99 |
        | output_account      |   -2375.99 |        -2375.99 |
        +---------------------+------------+-----------------+
        | Total balance       |       0.00 |            0.00 |
        +---------------------+------------+-----------------+
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product4, 7), (self.product5, 7)]))
        orders.append(self.create_ui_order_data([(self.product5, 6), (self.product4, 6), (self.product6, 49)]))
        orders.append(self.create_ui_order_data([(self.product5, 2), (self.product6, 13)]))
        orders.append(self.create_ui_order_data([(self.product6, 1)]))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_account_move = self.pos_session.move_id

        self.assertEqual(len(session_account_move.line_ids), 4, msg='There should exactly be 4 account move lines.')

        sales_line = session_account_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sales_line.balance, -7153.90, msg='Sales line balance should be equal to total orders amount.')
        self.assertAlmostEqual(sales_line.amount_currency, -3576.95)

        receivable_line_cash = session_account_move.line_ids.filtered(lambda line: self.pos_receivable_account == line.account_id and self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 7153.90, msg='Cash receivable should be equal to the total cash payments.')
        self.assertAlmostEqual(receivable_line_cash.amount_currency, 3576.95)

        expense_line = session_account_move.line_ids.filtered(lambda line: line.account_id == self.expense_account)
        self.assertAlmostEqual(expense_line.balance, 2375.99)
        self.assertAlmostEqual(expense_line.amount_currency, 2375.99)

        output_line = session_account_move.line_ids.filtered(lambda line: line.account_id == self.output_account)
        self.assertAlmostEqual(output_line.balance, -2375.99)
        self.assertAlmostEqual(output_line.amount_currency, -2375.99)

        self.assertTrue(receivable_line_cash.full_reconcile_id, msg='Cash receivable line should be fully-reconciled.')
        self.assertTrue(output_line.full_reconcile_id, msg='The stock output account line should be fully-reconciled.')

    def test_05_tax_base_amount(self):
        self.open_new_session()

        order = self.env['pos.order'].create_from_ui(
            [self.create_ui_order_data([(self.product7, 7)])]
        )
        self.pos_session.action_pos_session_validate()
        session_account_move = self.pos_session.move_id

        self.assertEqual(len(session_account_move.line_ids), 3, msg='There should exactly be 3 account move lines.')

        sales_line = session_account_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sales_line.balance, -49)
        self.assertAlmostEqual(sales_line.amount_currency, -24.5)

        receivable_line_cash = session_account_move.line_ids.filtered(lambda line: self.pos_receivable_account == line.account_id and self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 52.43)
        self.assertAlmostEqual(receivable_line_cash.amount_currency, 26.215)

        tax_line = session_account_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)
        self.assertAlmostEqual(tax_line.balance, -3.43)
        self.assertAlmostEqual(tax_line.amount_currency, -1.715)
        self.assertAlmostEqual(tax_line.tax_base_amount, 49, msg="Value should be in company's currency.")
