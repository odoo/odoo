import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSMultipleReceivableAccounts(TestPoSCommon):
    """ Test for invoiced orders with customers having receivable account different from default

    Thus, for this test, there are two receivable accounts involved and are set in the
    customers.
        self.customer -> self.receivable_account
        self.other_customer -> self.other_receivable_account

    NOTE That both receivable accounts above are different from the pos receivable account.
    """

    def setUp(self):
        super(TestPoSMultipleReceivableAccounts, self).setUp()
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

    def test_01_invoiced_order_from_other_customer(self):
        """
        Orders
        ======
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order   | payments | invoiced? | product  | qty | untaxed | tax                      | total  |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order 1 | cash     | no        | product1 | 10  | 109.9   | 7.69 [7%]                | 117.59 |
        |         |          |           | product2 | 10  | 181.73  | 18.17 [10%]              | 199.9  |
        |         |          |           | product3 | 10  | 281.73  | 19.72 [7%] + 28.17 [10%] | 329.62 |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order 2 | bank     | no        | product1 | 5   | 54.95   | 3.85 [7%]                | 58.80  |
        |         |          |           | product2 | 5   | 90.86   | 9.09 [10%]               | 99.95  |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order 3 | bank     | yes       | product2 | 5   | 90.86   | 9.09 [10%]               | 99.95  |
        |         |          |           | product3 | 5   | 140.86  | 9.86 [7%] + 14.09 [10%]  | 164.81 |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        | -164.85 |
        | sale_account        | -281.73 |
        | other_sale_account  | -272.59 |
        | tax 7%              |  -31.26 |
        | tax 10%             |  -55.43 |
        | pos receivable cash |  647.11 |
        | pos receivable bank |  423.51 |
        | other receivable    | -264.76 |
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
            customer=self.other_customer,
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

        session_move = self.pos_session.move_id
        # There should be no line corresponding the original receivable account
        # But there should be a line for other_receivable_account because
        # that is the property_account_receivable_id of the customer
        # of the invoiced order.
        receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertFalse(receivable_line, msg='There should be no move line for the original receivable account.')
        other_receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.other_receivable_account)
        self.assertAlmostEqual(other_receivable_line.balance, -264.76)

    def test_02_all_orders_invoiced_mixed_customers(self):
        """
        Orders
        ======
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+
        | order   | payments | invoiced?           | product  | qty | untaxed | tax                      |  total |
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+
        | order 1 | cash     | yes, other_customer | product1 |  10 |  109.90 | 7.69 [7%]                | 117.59 |
        |         |          |                     | product2 |  10 |  181.73 | 18.17 [10%]              | 199.90 |
        |         |          |                     | product3 |  10 |  281.73 | 19.72 [7%] + 28.17 [10%] | 329.62 |
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+
        | order 2 | bank     | yes, customer       | product1 |   5 |   54.95 | 3.85 [7%]                |  58.80 |
        |         |          |                     | product2 |   5 |   90.86 | 9.09 [10%]               |  99.95 |
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+
        | order 3 | bank     | yes, other customer | product2 |   5 |   90.86 | 9.09 [10%]               |  99.95 |
        |         |          |                     | product3 |   5 |  140.86 | 9.86 [7%] + 14.09 [10%]  | 164.81 |
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+

        Expected Result
        ===============
        +------------------+---------+
        | account          | balance |
        +------------------+---------+
        | receivable cash  |  647.11 |
        | receivable bank  |  423.51 |
        | other receivable | -911.87 |
        | receivable       | -158.75 |
        +------------------+---------+
        | Total balance    |    0.00 |
        +------------------+---------+

        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 10), (self.product2, 10), (self.product3, 10)],
            customer=self.other_customer,
            is_invoiced=True,
            uid='09876-098-0987',
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product2, 5)],
            payments=[(self.bank_pm, 158.75)],
            customer=self.customer,
            is_invoiced=True,
            uid='09876-098-0988',
        ))
        orders.append(self.create_ui_order_data(
            [(self.product2, 5), (self.product3, 5)],
            payments=[(self.bank_pm, 264.76)],
            customer=self.other_customer,
            is_invoiced=True,
            uid='09876-098-0989',
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # check if there is one invoiced order
        self.assertEqual(len(self.pos_session.order_ids.filtered(lambda order: order.state == 'invoiced')), 3, 'All orders should be invoiced.')

        # close the session
        self.pos_session.action_pos_session_validate()

        session_move = self.pos_session.move_id

        receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertAlmostEqual(receivable_line.balance, -158.75)
        other_receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.other_receivable_account)
        self.assertAlmostEqual(other_receivable_line.balance, -911.87)
        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 423.51)
        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 647.11)
