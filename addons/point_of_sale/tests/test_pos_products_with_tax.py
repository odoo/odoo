import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSProductsWithTax(TestPoSCommon):
    """ Test normal configuration PoS selling products with tax
    """

    def setUp(self):
        super(TestPoSProductsWithTax, self).setUp()
        self.config = self.basic_config
        self.product1 = self.create_product(
            'Product 1',
            self.categ_basic,
            10.0,
            5.0,
            tax_ids=self.taxes['tax7'].ids,
        )
        self.product2 = self.create_product(
            'Product 2',
            self.categ_basic,
            20.0,
            10.0,
            tax_ids=self.taxes['tax10'].ids,
        )
        self.product3 = self.create_product(
            'Product 3',
            self.categ_basic,
            30.0,
            15.0,
            tax_ids=self.taxes['tax_group_7_10'].ids,
        )
        self.adjust_inventory([self.product1, self.product2, self.product3], [100, 50, 50])

    def test_orders_no_invoiced(self):
        """ Test for orders without invoice

        Orders
        ======
        +---------+----------+-----------+----------+-----+---------+-----------------------+--------+
        | order   | payments | invoiced? | product  | qty | untaxed | tax                   |  total |
        +---------+----------+-----------+----------+-----+---------+-----------------------+--------+
        | order 1 | cash     | no        | product1 |  10 |     100 | 7                     |    107 |
        |         |          |           | product2 |   5 |   90.91 | 9.09                  |    100 |
        +---------+----------+-----------+----------+-----+---------+-----------------------+--------+
        | order 2 | cash     | no        | product2 |   7 |  127.27 | 12.73                 |    140 |
        |         |          |           | product3 |   4 |  109.09 | 10.91[10%] + 7.64[7%] | 127.64 |
        +---------+----------+-----------+----------+-----+---------+-----------------------+--------+
        | order 3 | bank     | no        | product1 |   1 |      10 | 0.7                   |   10.7 |
        |         |          |           | product2 |   3 |   54.55 | 5.45                  |     60 |
        |         |          |           | product3 |   5 |  136.36 | 13.64[10%] + 9.55[7%] | 159.55 |
        +---------+----------+-----------+----------+-----+---------+-----------------------+--------+

        Calculated taxes
        ================
            total tax 7% only + group tax (10+7%)
                (7 + 0.7) + (7.64 + 9.55) = 7.7 + 17.19 = 24.89
            total tax 10% only + group tax (10+7%)
                (9.09 + 12.73 + 5.45) + (10.91 + 13.64) = 27.27 + 24.55 = 51.82

        Thus, manually_calculated_taxes = (-24,89, -51.82)
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 10), (self.product2, 5)]))
        orders.append(self.create_ui_order_data([(self.product2, 7), (self.product3, 4)]))
        orders.append(self.create_ui_order_data(
            [(self.product1, 1), (self.product3, 5), (self.product2, 3)],
            payments=[(self.bank_pm, 230.25)]
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, 'Total order amount should be equal to the total payment amount.')

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sales_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sum(sales_lines.mapped('balance')), -628.18, msg='Sales line balance should be equal to untaxed orders amount.')

        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 230.25, msg='Bank receivable should be equal to the total bank payments.')

        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 474.64, msg='Cash receivable should be equal to the total cash payments.')

        tax_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)

        manually_calculated_taxes = (-24.89, -51.82)
        self.assertAlmostEqual(sum(manually_calculated_taxes), sum(tax_lines.mapped('balance')))
        for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
            self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined.')

        base_amounts = (355.45, 518.18)
        self.assertAlmostEqual(sum(base_amounts), sum(tax_lines.mapped('tax_base_amount')))

        self.assertTrue(receivable_line_cash.full_reconcile_id, 'Cash receivable line should be fully-reconciled.')

    def test_orders_with_invoiced(self):
        """ Test for orders: one with invoice

        Orders
        ======
        +---------+----------+---------------+----------+-----+---------+---------------+--------+
        | order   | payments | invoiced?     | product  | qty | untaxed | tax           |  total |
        +---------+----------+---------------+----------+-----+---------+---------------+--------+
        | order 1 | cash     | no            | product1 |   6 |      60 | 4.2           |   64.2 |
        |         |          |               | product2 |   3 |   54.55 | 5.45          |     60 |
        |         |          |               | product3 |   1 |   27.27 | 2.73 + 1.91   |  31.91 |
        +---------+----------+---------------+----------+-----+---------+---------------+--------+
        | order 2 | bank     | no            | product1 |   1 |      10 | 0.7           |   10.7 |
        |         |          |               | product2 |  20 |  363.64 | 36.36         |    400 |
        +---------+----------+---------------+----------+-----+---------+---------------+--------+
        | order 3 | bank     | yes, customer | product1 |  10 |     100 | 7             |    107 |
        |         |          |               | product3 |  10 |  272.73 | 27.27 + 19.09 | 319.09 |
        +---------+----------+---------------+----------+-----+---------+---------------+--------+

        Calculated taxes
        ================
            total tax 7% only
                4.2 + 0.7 => 4.9 + 1.91 = 6.81
            total tax 10% only
                5.45 + 36.36 => 41.81 + 2.73 = 44.54

        Thus, manually_calculated_taxes = (-6.81, -44.54)
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product3, 1), (self.product1, 6), (self.product2, 3)],
            payments=[(self.cash_pm, 156.11)],
        ))
        orders.append(self.create_ui_order_data(
            [(self.product2, 20), (self.product1, 1)],
            payments=[(self.bank_pm, 410.7)],
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 10), (self.product3, 10)],
            payments=[(self.bank_pm, 426.09)],
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

        # check account move in the invoiced order
        invoiced_order = self.pos_session.order_ids.filtered(lambda order: '09876-098-0987' in order.pos_reference)
        self.assertEqual(1, len(invoiced_order), 'Only one order is invoiced in this test.')
        invoice = invoiced_order.account_move
        self.assertAlmostEqual(invoice.amount_total, 426.09)

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        # check sales line
        # should not include tax amounts
        sales_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sum(sales_lines.mapped('balance')), -515.46)

        # check receivable line
        # should be equivalent to receivable in the invoice
        # should also be fully-reconciled
        receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertAlmostEqual(receivable_line.balance, -426.09)
        self.assertTrue(receivable_line.full_reconcile_id, msg='Receivable line for invoices should be fully reconciled.')

        pos_receivable_line_bank = session_move.line_ids.filtered(
            lambda line: self.bank_pm.name in line.name and line.account_id == self.bank_pm.receivable_account_id
        )
        self.assertAlmostEqual(pos_receivable_line_bank.balance, 836.79)

        pos_receivable_line_cash = session_move.line_ids.filtered(
            lambda line: self.cash_pm.name in line.name and line.account_id == self.bank_pm.receivable_account_id
        )
        self.assertAlmostEqual(pos_receivable_line_cash.balance, 156.11)
        self.assertTrue(pos_receivable_line_cash.full_reconcile_id)

        receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertAlmostEqual(receivable_line.balance, -invoice.amount_total)

        tax_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)

        manually_calculated_taxes = (-6.81, -44.54)
        self.assertAlmostEqual(sum(manually_calculated_taxes), sum(tax_lines.mapped('balance')))
        for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
            self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined.')

        base_amounts = (97.27, 445.46)  # computation does not include invoiced order.
        self.assertAlmostEqual(sum(base_amounts), sum(tax_lines.mapped('tax_base_amount')))

    def test_return_order(self):
        """ Test return order

        Order (invoiced)
        ======
        +----------+----------+---------------+----------+-----+---------+-------------+-------+
        | order    | payments | invoiced?     | product  | qty | untaxed | tax         | total |
        +----------+----------+---------------+----------+-----+---------+-------------+-------+
        | order 1  | cash     | yes, customer | product1 |   3 |      30 | 2.1         |  32.1 |
        |          |          |               | product2 |   2 |   36.36 | 3.64        |    40 |
        |          |          |               | product3 |   1 |   27.27 | 2.73 + 1.91 | 31.91 |
        +----------+----------+---------------+----------+-----+---------+-------------+-------+

        The order is invoiced so the tax of the invoiced order is in the account_move of the order.
        However, the return order is not invoiced, thus, the journal items are in the session_move,
        which will contain the tax lines of the returned products.

        manually_calculated_taxes = (4.01, 6.37)
        """
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 2), (self.product3, 1)],
            payments=[(self.cash_pm, 104.01)],
            customer=self.customer,
            is_invoiced=True,
            uid='12345-123-1234',
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(1, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # return order
        order_to_return = self.pos_session.order_ids.filtered(lambda order: '12345-123-1234' in order.pos_reference)
        order_to_return.refund()

        refund_order = self.pos_session.order_ids.filtered(lambda order: order.state == 'draft')
        context_make_payment = {"active_ids": [refund_order.id], "active_id": refund_order.id}
        make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
            'payment_method_id': self.cash_pm.id,
            'amount': -104.01,
        })
        make_payment.check()
        self.assertEqual(refund_order.state, 'paid', 'Payment is registered, order should be paid.')
        self.assertAlmostEqual(refund_order.amount_paid, -104.01, msg='Amount paid for return order should be negative.')

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        # instead of credit, the sales line should be debit
        sales_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sum(sales_lines.mapped('balance')), 93.63)

        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertFalse(receivable_line_bank, msg='There should be no bank receivable line because no bank payment made.')

        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertFalse(receivable_line_cash, msg='There should be no cash receivable line because it is combined with the original cash payment.')

        manually_calculated_taxes = (4.01, 6.37)  # should be positive since it is return order
        tax_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)
        self.assertAlmostEqual(sum(manually_calculated_taxes), sum(tax_lines.mapped('balance')))
        for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
            self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined and should be debit.')
