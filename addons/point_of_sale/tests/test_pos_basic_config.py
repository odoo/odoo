import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSBasicConfig(TestPoSCommon):
    """ Test PoS with basic configuration

    The tests contain base scenarios in using pos.
    More specialized cases are tested in other tests.
    """

    def setUp(self):
        super(TestPoSBasicConfig, self).setUp()
        self.config = self.basic_config
        self.product0 = self.create_product('Product 0', self.categ_basic, 0.0, 0.0)
        self.product1 = self.create_product('Product 1', self.categ_basic, 10.0, 5)
        self.product2 = self.create_product('Product 2', self.categ_basic, 20.0, 10)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15)
        self.product4 = self.create_product('Product_4', self.categ_basic, 9.96, 4.98)
        self.adjust_inventory([self.product1, self.product2, self.product3], [100, 50, 50])

    def test_orders_no_invoiced(self):
        """ Test for orders without invoice

        3 orders
        - first 2 orders with cash payment
        - last order with bank payment

        Orders
        ======
        +---------+----------+-----------+----------+-----+-------+
        | order   | payments | invoiced? | product  | qty | total |
        +---------+----------+-----------+----------+-----+-------+
        | order 1 | cash     | no        | product1 |  10 |   100 |
        |         |          |           | product2 |   5 |   100 |
        +---------+----------+-----------+----------+-----+-------+
        | order 2 | cash     | no        | product2 |   7 |   140 |
        |         |          |           | product3 |   1 |    30 |
        +---------+----------+-----------+----------+-----+-------+
        | order 3 | bank     | no        | product1 |   1 |    10 |
        |         |          |           | product2 |   3 |    60 |
        |         |          |           | product3 |   5 |   150 |
        +---------+----------+-----------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale                |    -590 |
        | pos receivable cash |     370 |
        | pos receivable bank |     220 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """
        start_qty_available = {
            self.product1: self.product1.qty_available,
            self.product2: self.product2.qty_available,
            self.product3: self.product3.qty_available,
        }

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product1, 10), (self.product2, 5)]))
        orders.append(self.create_ui_order_data([(self.product2, 7), (self.product3, 1)]))
        orders.append(self.create_ui_order_data(
            [(self.product1, 1), (self.product3, 5), (self.product2, 3)],
            payments=[(self.bank_pm, 220)]
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # check product qty_available after syncing the order
        self.assertEqual(
            self.product1.qty_available + 11,
            start_qty_available[self.product1],
        )
        self.assertEqual(
            self.product2.qty_available + 15,
            start_qty_available[self.product2],
        )
        self.assertEqual(
            self.product3.qty_available + 6,
            start_qty_available[self.product3],
        )

        # picking and stock moves should be in done state
        for order in self.pos_session.order_ids:
            self.assertEqual(
                order.picking_id.state,
                'done',
                'Picking should be in done state.'
            )
            move_lines = order.picking_id.move_lines
            self.assertEqual(
                move_lines.mapped('state'),
                ['done'] * len(move_lines),
                'Move Lines should be in done state.'
            )

        # close the session
        self.pos_session.action_pos_session_validate()

        # check accounting values after the session is closed
        session_move = self.pos_session.move_id

        sales_line = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sales_line.balance, -590.0, msg='Sales line balance should be equal to total orders amount.')

        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 220.0, msg='Bank receivable should be equal to the total bank payments.')

        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 370.0, msg='Cash receivable should be equal to the total cash payments.')

        self.assertTrue(receivable_line_cash.full_reconcile_id, msg='Cash receivable line should be fully-reconciled.')

    def test_orders_with_invoiced(self):
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
        | order 1 | cash     | no            | product1 |   6 |    60 |
        |         |          |               | product2 |   3 |    60 |
        |         |          |               | product3 |   1 |    30 |
        +---------+----------+---------------+----------+-----+-------+
        | order 2 | bank     | no            | product1 |   1 |    10 |
        |         |          |               | product2 |  20 |   400 |
        +---------+----------+---------------+----------+-----+-------+
        | order 3 | bank     | yes, customer | product1 |  10 |   100 |
        |         |          |               | product3 |   1 |    30 |
        +---------+----------+---------------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale                |    -560 |
        | pos receivable cash |     150 |
        | pos receivable bank |     540 |
        | receivable          |    -130 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """
        start_qty_available = {
            self.product1: self.product1.qty_available,
            self.product2: self.product2.qty_available,
            self.product3: self.product3.qty_available,
        }

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product3, 1), (self.product1, 6), (self.product2, 3)],
            payments=[(self.cash_pm, 150)],
        ))
        orders.append(self.create_ui_order_data(
            [(self.product2, 20), (self.product1, 1)],
            payments=[(self.bank_pm, 410)],
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 10), (self.product3, 1)],
            payments=[(self.bank_pm, 130)],
            customer=self.customer,
            is_invoiced=True,
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # check product qty_available after syncing the order
        self.assertEqual(
            self.product1.qty_available + 17,
            start_qty_available[self.product1],
        )
        self.assertEqual(
            self.product2.qty_available + 23,
            start_qty_available[self.product2],
        )
        self.assertEqual(
            self.product3.qty_available + 2,
            start_qty_available[self.product3],
        )

        # picking and stock moves should be in done state
        # no exception for invoiced orders
        for order in self.pos_session.order_ids:
            self.assertEqual(
                order.picking_id.state,
                'done',
                'Picking should be in done state.'
            )
            move_lines = order.picking_id.move_lines
            self.assertEqual(
                move_lines.mapped('state'),
                ['done'] * len(move_lines),
                'Move Lines should be in done state.'
            )

        # check account move in the invoiced order
        invoiced_order = self.pos_session.order_ids.filtered(lambda order: order.account_move)
        self.assertEqual(1, len(invoiced_order), 'Only one order is invoiced in this test.')
        invoice = invoiced_order.account_move
        self.assertAlmostEqual(invoice.amount_total, 130, msg='Amount total should be 130. Product is untaxed.')
        invoice_receivable_line = invoice.line_ids.filtered(lambda line: line.account_id == self.receivable_account)

        # check state of orders before validating the session.
        self.assertEqual('invoiced', invoiced_order.state, msg="state should be 'invoiced' for invoiced orders.")
        uninvoiced_orders = self.pos_session.order_ids - invoiced_order
        self.assertTrue(
            all([order.state == 'paid' for order in uninvoiced_orders]),
            msg="state should be 'paid' for uninvoiced orders before validating the session."
        )

        # close the session
        self.pos_session.action_pos_session_validate()

        # check state of orders after validating the session.
        self.assertTrue(
            all([order.state == 'done' for order in uninvoiced_orders]),
            msg="State should be 'done' for uninvoiced orders after validating the session."
        )

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sales_line = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertAlmostEqual(sales_line.balance, -(orders_total - invoice.amount_total), msg='Sales line should be total order minus invoiced order.')

        pos_receivable_line_bank = session_move.line_ids.filtered(
            lambda line: self.bank_pm.name in line.name and line.account_id == self.bank_pm.receivable_account_id
        )
        self.assertAlmostEqual(pos_receivable_line_bank.balance, 540.0, msg='Bank receivable should be equal to the total bank payments.')

        pos_receivable_line_cash = session_move.line_ids.filtered(
            lambda line: self.cash_pm.name in line.name and line.account_id == self.bank_pm.receivable_account_id
        )
        self.assertAlmostEqual(pos_receivable_line_cash.balance, 150.0, msg='Cash receivable should be equal to the total cash payments.')

        receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertAlmostEqual(receivable_line.balance, -invoice.amount_total)

        # cash receivable and invoice receivable lines should be fully reconciled
        self.assertTrue(pos_receivable_line_cash.full_reconcile_id)
        self.assertTrue(receivable_line.full_reconcile_id)

        # matching number of the receivable lines should be the same
        self.assertEqual(receivable_line.full_reconcile_id, invoice_receivable_line.full_reconcile_id)

    def test_orders_with_zero_valued_invoiced(self):
        """One invoiced order but with zero receivable line balance."""

        self.open_new_session()
        orders = [self.create_ui_order_data([(self.product0, 1)], payments=[(self.bank_pm, 0)], customer=self.customer, is_invoiced=True)]
        self.env['pos.order'].create_from_ui(orders)
        self.pos_session.action_pos_session_validate()

        invoice = self.pos_session.order_ids.account_move
        invoice_receivable_line = invoice.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        receivable_line = self.pos_session.move_id.line_ids.filtered(lambda line: line.account_id == self.receivable_account)

        self.assertTrue(invoice_receivable_line.reconciled)
        self.assertTrue(receivable_line.reconciled)

    def test_return_order_invoiced(self):
        self.open_new_session()

        # create order
        orders = [
            self.create_ui_order_data([(self.product1, 10)], payments=[(self.cash_pm, 100)], customer=self.customer,
                                      is_invoiced=True, uid='666-666-666')]
        self.env['pos.order'].create_from_ui(orders)
        order = self.pos_session.order_ids.filtered(lambda order: '666-666-666' in order.pos_reference)

        # refund
        order.refund()
        refund_order = self.pos_session.order_ids.filtered(lambda order: order.state == 'draft')

        # pay the refund
        context_make_payment = {"active_ids": [refund_order.id], "active_id": refund_order.id}
        make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
            'payment_method_id': self.cash_pm.id,
            'amount': -100,
        })
        make_payment.check()

        # invoice refund
        refund_order.action_pos_order_invoice()

        # close the session -- just verify, that there are no errors
        self.pos_session.action_pos_session_validate()

    def test_return_order(self):
        """ Test return order

        2 orders
        - 2nd order is returned

        Orders
        ======
        +------------------+----------+-----------+----------+-----+-------+
        | order            | payments | invoiced? | product  | qty | total |
        +------------------+----------+-----------+----------+-----+-------+
        | order 1          | bank     | no        | product1 |   1 |    10 |
        |                  |          |           | product2 |   5 |   100 |
        +------------------+----------+-----------+----------+-----+-------+
        | order 2          | cash     | no        | product1 |   3 |    30 |
        |                  |          |           | product2 |   2 |    40 |
        |                  |          |           | product3 |   1 |    30 |
        +------------------+----------+-----------+----------+-----+-------+
        | order 3 (return) | cash     | no        | product1 |  -3 |   -30 |
        |                  |          |           | product2 |  -2 |   -40 |
        |                  |          |           | product3 |  -1 |   -30 |
        +------------------+----------+-----------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale (sales)        |    -210 |
        | sale (refund)       |     100 |
        | pos receivable bank |     110 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """
        start_qty_available = {
            self.product1: self.product1.qty_available,
            self.product2: self.product2.qty_available,
            self.product3: self.product3.qty_available,
        }

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 1), (self.product2, 5)],
            payments=[(self.bank_pm, 110)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 2), (self.product3, 1)],
            payments=[(self.cash_pm, 100)],
            uid='12345-123-1234'
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(2, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # return order
        order_to_return = self.pos_session.order_ids.filtered(lambda order: '12345-123-1234' in order.pos_reference)
        order_to_return.refund()
        refund_order = self.pos_session.order_ids.filtered(lambda order: order.state == 'draft')

        # check if amount to pay
        self.assertAlmostEqual(refund_order.amount_total - refund_order.amount_paid, -100)

        # pay the refund
        context_make_payment = {"active_ids": [refund_order.id], "active_id": refund_order.id}
        make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
            'payment_method_id': self.cash_pm.id,
            'amount': -100,
        })
        make_payment.check()
        self.assertEqual(refund_order.state, 'paid', 'Payment is registered, order should be paid.')
        self.assertAlmostEqual(refund_order.amount_paid, -100.0, msg='Amount paid for return order should be negative.')

        # check product qty_available after syncing the order
        self.assertEqual(
            self.product1.qty_available + 1,
            start_qty_available[self.product1],
        )
        self.assertEqual(
            self.product2.qty_available + 5,
            start_qty_available[self.product2],
        )
        self.assertEqual(
            self.product3.qty_available,
            start_qty_available[self.product3],
        )

        # picking and stock moves should be in done state
        # no exception of return orders
        for order in self.pos_session.order_ids:
            self.assertEqual(
                order.picking_id.state,
                'done',
                'Picking should be in done state.'
            )
            move_lines = order.picking_id.move_lines
            self.assertEqual(
                move_lines.mapped('state'),
                ['done'] * len(move_lines),
                'Move Lines should be in done state.'
            )

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sale_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertEqual(len(sale_lines), 2, msg='There should be lines for both sales and refund.')
        self.assertAlmostEqual(sum(sale_lines.mapped('balance')), -110.0)

        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 110.0)

        # net cash in the session is zero, thus, there should be no receivable cash line.
        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertFalse(receivable_line_cash, 'There should be no receivable cash line because both the order and return order are paid with cash - they cancelled.')

    def test_split_cash_payments(self):
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 10), (self.product2, 5)],
            payments=[(self.cash_split_pm, 100), (self.bank_pm, 100)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product2, 7), (self.product3, 1)],
            payments=[(self.cash_split_pm, 70), (self.bank_pm, 100)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 1), (self.product3, 5), (self.product2, 3)],
            payments=[(self.cash_split_pm, 120), (self.bank_pm, 100)]
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        account_move = self.pos_session.move_id

        bank_receivable_lines = account_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertEqual(len(bank_receivable_lines), 1, msg='Bank receivable lines should only have one line because it\'s supposed to be combined.')
        self.assertAlmostEqual(bank_receivable_lines.balance, 300.0, msg='Bank receivable should be equal to the total bank payments.')

        cash_receivable_lines = account_move.line_ids.filtered(lambda line: self.cash_split_pm.name in line.name)
        self.assertEqual(len(cash_receivable_lines), 3, msg='There should be a number of cash receivable lines because the cash_pm is `split_transactions`.')
        self.assertAlmostEqual(sum(cash_receivable_lines.mapped('balance')), 290, msg='Total cash receivable balance should be equal to the total cash payments.')

        for line in cash_receivable_lines:
            self.assertTrue(line.full_reconcile_id, msg='Each cash receivable line should be fully-reconciled.')


    def test_correct_partner_on_invoice_receivables(self):
        self.open_new_session()

        # create orders
        # each order with total amount of 100.
        orders = []
        # from 1st to 8th order: use the same customer (self.customer) but varies with is_invoiced and payment method.
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.cash_pm, 100)], customer=self.customer, is_invoiced=True, uid='00100-010-0001'))
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.bank_pm, 100)], customer=self.customer, is_invoiced=True, uid='00100-010-0002'))
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.cash_split_pm, 100)], customer=self.customer, is_invoiced=True, uid='00100-010-0003'))
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.bank_split_pm, 100)], customer=self.customer, is_invoiced=True, uid='00100-010-0004'))
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.cash_pm, 100)], customer=self.customer, uid='00100-010-0005'))
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.bank_pm, 100)], customer=self.customer, uid='00100-010-0006'))
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.cash_split_pm, 100)], customer=self.customer, uid='00100-010-0007'))
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.bank_split_pm, 100)], customer=self.customer, uid='00100-010-0008'))
        # 9th and 10th orders for self.other_customer, both invoiced and paid by bank
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.bank_pm, 100)], customer=self.other_customer, is_invoiced=True, uid='00100-010-0009'))
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.bank_pm, 100)], customer=self.other_customer, is_invoiced=True, uid='00100-010-0010'))
        # 11th order: invoiced to self.customer with bank payment method
        orders.append(self.create_ui_order_data([(self.product1, 10)], payments=[(self.bank_pm, 100)], customer=self.customer, is_invoiced=True, uid='00100-010-0011'))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # close the session
        self.pos_session.action_pos_session_validate()

        # self.customer's bank split payments
        customer_pos_receivable_bank = self.pos_session.move_id.line_ids.filtered(lambda line: line.partner_id == self.customer and 'Split (Bank) PM' in line.name)
        self.assertEqual(len(customer_pos_receivable_bank), 2, msg='there are 2 bank split payments from self.customer')
        self.assertEqual(bool(customer_pos_receivable_bank.full_reconcile_id), False, msg="the pos (bank) receivable lines shouldn't be reconciled")

        # self.customer's cash split payments
        customer_pos_receivable_cash = self.pos_session.move_id.line_ids.filtered(lambda line: line.partner_id == self.customer and 'Split (Cash) PM' in line.name)
        self.assertEqual(len(customer_pos_receivable_cash), 2, msg='there are 2 cash split payments from self.customer')
        self.assertEqual(bool(customer_pos_receivable_cash.full_reconcile_id), True, msg="cash pos (cash) receivable lines should be reconciled")

        # self.customer's invoice receivable counterpart
        customer_invoice_receivable_counterpart = self.pos_session.move_id.line_ids.filtered(lambda line: line.partner_id == self.customer and 'From invoiced orders' in line.name)
        self.assertEqual(len(customer_invoice_receivable_counterpart), 1, msg='there should one aggregated invoice receivable counterpart for self.customer')
        self.assertEqual(bool(customer_invoice_receivable_counterpart.full_reconcile_id), True, msg='the aggregated receivable for self.customer should be reconciled')
        self.assertEqual(customer_invoice_receivable_counterpart.balance, -500, msg='aggregated balance should be -500')

        # self.other_customer also made invoiced orders
        # therefore, it should also have aggregated receivable counterpart in the session's account_move
        other_customer_invoice_receivable_counterpart = self.pos_session.move_id.line_ids.filtered(lambda line: line.partner_id == self.other_customer and 'From invoiced orders' in line.name)
        self.assertEqual(len(other_customer_invoice_receivable_counterpart), 1, msg='there should one aggregated invoice receivable counterpart for self.other_customer')
        self.assertEqual(bool(other_customer_invoice_receivable_counterpart.full_reconcile_id), True, msg='the aggregated receivable for self.other_customer should be reconciled')
        self.assertEqual(other_customer_invoice_receivable_counterpart.balance, -200, msg='aggregated balance should be -200')

    def test_refund_customer_reconcile(self):
        """ Test return invoiced order

                2 orders
                - 2nd order is returned

                Orders
                ======
                +------------------+----------+-----------+----------+-----+-------+
                | order            | payments | invoiced? | product  | qty | total |
                +------------------+----------+-----------+----------+-----+-------+
                | order 1          | bank     | yes       | product1 |   3 |    30 |
                |                  |          |           | product2 |   2 |    40 |
                |                  |          |           | product3 |   1 |    30 |
                +------------------+----------+-----------+----------+-----+-------+
                | order 2          | bank     | yes       | product1 |   3 |    30 |
                |                  |          |           | product2 |   2 |    40 |
                |                  |          |           | product3 |   1 |    30 |
                +------------------+----------+-----------+----------+-----+-------+
                | order 3 (return) | bank     | yes       | product1 |  -3 |   -30 |
                |                  |          |           | product2 |  -2 |   -40 |
                |                  |          |           | product3 |  -1 |   -30 |
                +------------------+----------+-----------+----------+-----+-------+

                Expected Result
                ===============
                +---------------------+---------+
                | account             | balance |
                +---------------------+---------+
                | receivable          |    -100 |
                | pos receivable bank |     100 |
                +---------------------+---------+
                | Total balance       |     0.0 |
                +---------------------+---------+
                """
        start_qty_available = {
            self.product1: self.product1.qty_available,
            self.product2: self.product2.qty_available,
            self.product3: self.product3.qty_available,
        }

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 2), (self.product3, 1)],
            payments=[(self.bank_pm, 100)],
            is_invoiced=True,
            uid='12346-123-1234',
            customer=self.customer
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 2), (self.product3, 1)],
            payments=[(self.bank_pm, 100)],
            uid='12345-123-1234',
            is_invoiced=True,
            customer=self.customer
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(2, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount,
                               msg='Total order amount should be equal to the total payment amount.')

        # return order
        order_to_return = self.pos_session.order_ids.filtered(
            lambda order: '12345-123-1234' in order.pos_reference)
        order_to_return.refund()
        refund_order = self.pos_session.order_ids.filtered(
            lambda order: order.state == 'draft')

        # check if amount to pay
        self.assertAlmostEqual(refund_order.amount_total - refund_order.amount_paid,
                               -100)

        # pay the refund
        context_make_payment = {"active_ids": [refund_order.id],
                                "active_id": refund_order.id}
        make_payment = self.env['pos.make.payment'].with_context(
            context_make_payment).create({
            'payment_method_id': self.bank_pm.id,
            'amount': -100,
        })
        make_payment.check()
        self.assertEqual(refund_order.state, 'paid',
                         'Payment is registered, order should be paid.')
        self.assertAlmostEqual(refund_order.amount_paid, -100.0,
                               msg='Amount paid for return order should be negative.')
        refund_order.action_pos_order_invoice()
        self.assertTrue(refund_order.account_move)
        # check product qty_available after syncing the order
        self.assertEqual(
            self.product1.qty_available + 3,
            start_qty_available[self.product1],
        )
        self.assertEqual(
            self.product2.qty_available + 2,
            start_qty_available[self.product2],
        )
        self.assertEqual(
            self.product3.qty_available + 1,
            start_qty_available[self.product3],
        )

        # picking and stock moves should be in done state
        # no exception of return orders
        for order in self.pos_session.order_ids:
            self.assertEqual(
                order.picking_id.state,
                'done',
                'Picking should be in done state.'
            )
            move_lines = order.picking_id.move_lines
            self.assertEqual(
                move_lines.mapped('state'),
                ['done'] * len(move_lines),
                'Move Lines should be in done state.'
            )

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sale_lines = session_move.line_ids.filtered(
            lambda line: line.account_id == self.sale_account)
        self.assertEqual(len(sale_lines), 0,
                         msg='There should be no lines as all is invoiced.')
        self.assertEqual(
            sum(session_move.line_ids.filtered(
                lambda line: line.partner_id == self.customer
            ).mapped("balance")),
            -100
        )
        receivable_line_bank = session_move.line_ids.filtered(
            lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 100.0)
        for order in self.pos_session.order_ids:
            self.assertEqual(0, order.account_move.amount_residual)

    def test_multiple_customers_reconcile(self):
        """ Test return invoiced order from another customer

                2 actions
                - 1st order from one customer
                - 2nd order is a refund from another customer

                Orders
                ======
                +------------------+----------+-----------+----------+-----+-------+
                | order            | payments | invoiced? | product  | qty | total |
                +------------------+----------+-----------+----------+-----+-------+
                | order 1          | bank     | yes       | product1 |   3 |    30 |
                |                  |          | customer  | product2 |   2 |    40 |
                |                  |          |           | product3 |   1 |    30 |
                +------------------+----------+-----------+----------+-----+-------+
                | order 2 (return) | bank     | yes       | product1 |  -3 |   -30 |
                |                  |          | other     | product2 |  -2 |   -40 |
                |                  |          | customer  | product3 |  -1 |   -30 |
                +------------------+----------+-----------+----------+-----+-------+

                Expected Result
                ===============
                +---------------------------+---------+
                | account                   | balance |
                +---------------------------+---------+
                | receivable customer       |    -100 |
                | receivable other customer |     100 |
                | pos receivable bank       |       0 |
                +---------------------------+---------+
                | Total balance             |     0.0 |
                +---------------------------+---------+
                """
        start_qty_available = {
            self.product1: self.product1.qty_available,
            self.product2: self.product2.qty_available,
            self.product3: self.product3.qty_available,
        }

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 2), (self.product3, 1)],
            payments=[(self.bank_pm, 100)],
            is_invoiced=True,
            uid='12346-123-1234',
            customer=self.customer
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, -3), (self.product2, -2), (self.product3, -1)],
            payments=[(self.bank_pm, -100)],
            uid='12345-123-1234',
            is_invoiced=True,
            customer=self.other_customer
        ))

        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(2, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount,
                               msg='Total order amount should be equal to the total payment amount.')
        self.assertEqual(
            self.product1.qty_available,
            start_qty_available[self.product1],
        )
        self.assertEqual(
            self.product2.qty_available,
            start_qty_available[self.product2],
        )
        self.assertEqual(
            self.product3.qty_available,
            start_qty_available[self.product3],
        )

        # picking and stock moves should be in done state
        # no exception of return orders
        for order in self.pos_session.order_ids:
            self.assertEqual(
                order.picking_id.state,
                'done',
                'Picking should be in done state.'
            )
            move_lines = order.picking_id.move_lines
            self.assertEqual(
                move_lines.mapped('state'),
                ['done'] * len(move_lines),
                'Move Lines should be in done state.'
            )

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sale_lines = session_move.line_ids.filtered(
            lambda line: line.account_id == self.sale_account)
        self.assertEqual(len(sale_lines), 0,
                         msg='There should be no lines as all is invoiced.')

        self.assertEqual(
            session_move.line_ids.filtered(
                lambda line: line.partner_id == self.customer
            ).balance,
            -100
        )
        self.assertEqual(
            session_move.line_ids.filtered(
                lambda line: line.partner_id == self.other_customer
            ).balance,
            100
        )
        receivable_line_bank = session_move.line_ids.filtered(
            lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 0.0)
        for order in self.pos_session.order_ids:
            self.assertEqual(0, order.account_move.amount_residual)
