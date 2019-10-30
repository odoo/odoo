import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tools import float_is_zero

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSZeroTaxAndSales(TestPoSCommon):
    """ This is to test that sales of products with tax=0% is allowed.

    1. Sales lines from products with tax=0% are created containing the tax=0% in its tax_ids field.
    2. However, tax lines for tax=0% are not created because they have zero balance.
    """

    def setUp(self):
        super(TestPoSZeroTaxAndSales, self).setUp()
        self.config = self.basic_config
        self.tax0 = self.taxes['tax0']
        self.tax7 = self.taxes['tax7']
        self.tax_0_7 = self.tax0 | self.tax7
        self.product1 = self.create_product('Product 1', self.categ_basic, 10.0, 5, tax_ids=self.tax0.ids)
        self.product2 = self.create_product('Product 2', self.categ_basic, 0, 0, tax_ids=self.tax7.ids)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15, tax_ids=self.tax_0_7.ids)
        self.adjust_inventory([self.product1, self.product2, self.product3], [100, 50, 50])

    def test_zero_tax_on_sales_lines(self):
        """ Sales lines derived from product with tax=0% should still contain references to
        the 0% tax.

        Orders
        ======
        +---------+----------+----------+-----+---------+-----+-------+------------+
        | order   | payments | product  | qty | untaxed | tax | total | taxes      |
        +---------+----------+----------+-----+---------+-----+-------+------------+
        | order 1 | cash     | product1 | 2   | 20      | 0   | 20    | tax0       |
        +---------+----------+----------+-----+---------+-----+-------+------------+
        | order 2 | cash     | product3 | 3   | 90      | 6.3 | 96.3  | tax0, tax7 |
        +---------+----------+----------+-----+---------+-----+-------+------------+

        Results
        =======
        +---------------------+------------+---------+
        | account             | taxes      | balance |
        +---------------------+------------+---------+
        | sale_account        | tax0       | -20     |
        | sale_account        | tax0, tax7 | -90     |
        | tax 7%              |            | -6.3    |
        | pos receivable-cash |            | 116.3   |
        +---------------------+------------+---------+

        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 2)]))
        orders.append(self.create_ui_order_data([(self.product3, 3)]))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # close the session
        self.pos_session.action_pos_session_validate()

        # check accounting values after the session is closed
        session_move = self.pos_session.move_id

        sale_line_tax0 = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account and line.tax_ids == self.tax0)
        self.assertAlmostEqual(sale_line_tax0.balance, -20.0, msg='There should only be one line for 0% tax and balance should be -20.0.')

        sale_line_tax0_7 = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account and line.tax_ids == self.tax_0_7)
        self.assertAlmostEqual(sale_line_tax0_7.balance, -90.0, msg='There should only be one line for 0% and 7% taxes and balance should be -90.0.')

        zero_balance_line = session_move.line_ids.filtered(lambda line: float_is_zero(line.balance, precision_rounding=self.pos_session.currency_id.rounding))
        self.assertFalse(zero_balance_line, msg='There should be no line with zero balance.')

        pos_receivable_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(pos_receivable_cash.balance, 116.3)

    def test_selling_only_zero_cost_products(self):
        """ Account move should not be created if the session only contains zero-cost orders.
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product2, 5)]))
        orders.append(self.create_ui_order_data([(self.product2, 3)]))
        orders.append(self.create_ui_order_data([(self.product2, 1)]))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # close the session
        self.pos_session.action_pos_session_validate()

        self.assertFalse(self.pos_session.move_id, msg="There shouldn't be any move_id because the sales is zero.")


    def test_no_zero_balanced_sales_lines(self):
        """ No sales line should correspond to zero-cost products.

        Orders
        ======
        +---------+----------+----------+-----+---------+-----+-------+------------+
        | order   | payments | product  | qty | untaxed | tax | total | taxes      |
        +---------+----------+----------+-----+---------+-----+-------+------------+
        | order 1 | cash     | product1 | 5   | 50      | 0   | 50    | tax0       |
        +---------+----------+----------+-----+---------+-----+-------+------------+
        | order 2 | bank     | product2 | 3   | 0       | 0   | 0     | tax7       |
        +---------+----------+----------+-----+---------+-----+-------+------------+
        | order 3 | cash     | product3 | 1   | 30      | 2.1 | 32.1  | tax0, tax7 |
        +---------+----------+----------+-----+---------+-----+-------+------------+

        Results
        =======
        +---------------------+------------+---------+
        | account             | taxes      | balance |
        +---------------------+------------+---------+
        | sale_account        | tax0       | -50     |
        | sale_account        | tax0, tax7 | -30     |
        | tax 7%              |            | -2.1    |
        | pos receivable-cash |            | 82.1    |
        +---------------------+------------+---------+
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 5)]))
        orders.append(self.create_ui_order_data([(self.product2, 3)], payments=[(self.bank_pm, 0.0)]))
        orders.append(self.create_ui_order_data([(self.product3, 1)]))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # close the session
        self.pos_session.action_pos_session_validate()

        # check accounting values after the session is closed
        session_move = self.pos_session.move_id

        # product2 has 7% tax only. A sale line for this product should be created.
        # However, the product's price is zero therefore no sale line should be created for this product.
        sale_line_tax7_only = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account and line.tax_ids == self.tax7)
        self.assertFalse(sale_line_tax7_only, msg="There shouldn't be any sales line with 7% tax only.")

        sale_line_tax0 = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account and line.tax_ids == self.tax0)
        self.assertAlmostEqual(sale_line_tax0.balance, -50.0, msg='There should only be one line for 0% tax and balance should be -50.0.')

        sale_line_tax0_7 = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account and line.tax_ids == self.tax_0_7)
        self.assertAlmostEqual(sale_line_tax0_7.balance, -30.0, msg='There should only be one line for 0% and 7% taxes and balance should be -30.0.')

        pos_receivable_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(pos_receivable_cash.balance, 82.1)

        self.assertEqual(len(session_move.line_ids), 4, msg='There should be a total of 4 lines.')

        zero_balance_line = session_move.line_ids.filtered(lambda line: float_is_zero(line.balance, precision_rounding=self.pos_session.currency_id.rounding))
        self.assertFalse(zero_balance_line, msg='There should be not zero-valued line.')
