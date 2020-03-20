import odoo
from odoo.addons.point_of_sale.tests.test_pos_basic_config import TestPoSBasicConfig

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSCashRounding(TestPoSBasicConfig):
    """ Test PoS with basic configuration

    The tests contain base scenarios in using pos.
    More specialized cases are tested in other tests.
    """

    def test_rounding_method(self):
        # set the cash rounding method
        self.config.cash_rounding = True
        self.config.rounding_method = self.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'account_id': self.company['default_cash_difference_income_account_id'].copy().id,
            'loss_account_id': self.company['default_cash_difference_expense_account_id'].copy().id,
            'rounding_method': 'HALF-UP',
        })

        self.open_new_session()

        """ Test for orders: one with invoice

        3 orders
        - order 1, paid by cash
        - order 2, paid by bank
        - order 3, paid by bank, invoiced

        Orders
        ======
        +---------+----------+---------------+----------+-----+-------+
        | order   | payments | invoiced?     | product  | qty | total |
        +---------+----------+---------------+----------+-----+-------+
        | order 1 | bank     | no            | product1 |   6 |    60 |
        |         |          |               | product4 |   4 | 39.84 |
        +---------+----------+---------------+----------+-----+-------+
        | order 2 | bank     | yes           | product4 |   3 | 29.88 |
        |         |          |               | product2 |  20 |   400 |
        +---------+----------+---------------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale                | -596,56 |
        | pos receivable bank |  516,64 |
        | Rounding applied    |   -0,01 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """

        # create orders
        orders = []

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product4, 3), (self.product2, 20)],
            payments=[(self.bank_pm, 429.90)]
        ))

        orders.append(self.create_ui_order_data(
            [(self.product1, 6), (self.product4, 4)],
            payments=[(self.bank_pm, 99.85)]
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        self.assertEqual(orders[0]['data']['amount_return'], 0, msg='The amount return should be 0')
        self.assertEqual(orders[1]['data']['amount_return'], 0, msg='The amount return should be 0')

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_account_move = self.pos_session.move_id

        rounding_line = session_account_move.line_ids.filtered(lambda line: line.name == 'Rounding line')
        self.assertAlmostEqual(rounding_line.credit, 0.03, msg='The credit should be equals to 0.03')
