# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.point_of_sale.tests.test_pos_basic_config import TestPoSBasicConfig
from odoo.addons.pos_stock.tests.common import TestPosStockCommon


class TestPoSStockBasicConfig(TestPoSBasicConfig, TestPosStockCommon):
    """ Test PoS with basic configuration

    The tests contain base scenarios in using pos.
    More specialized cases are tested in other tests.
    """

    def setUp(self):
        super().setUp()
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

        def _before_closing_cb():
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
                    order.picking_ids[0].state,
                    'done',
                    'Picking should be in done state.'
                )
                move_ids = order.picking_ids[0].move_ids
                self.assertEqual(
                    move_ids.mapped('state'),
                    ['done'] * len(move_ids),
                    'Move Lines should be in done state.'
                )

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 5)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product2, 7), (self.product3, 1)], 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product3, 5), (self.product2, 3)], 'payments': [(self.bank_pm1, 220)], 'uuid': '00100-010-0003'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 590, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 220, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 370, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((370, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 370, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 370, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((220, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 220, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 220, 'reconciled': True},
                        ]
                    }),
                ],
            },
        })

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

        def _before_closing_cb():
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
                    order.picking_ids[0].state,
                    'done',
                    'Picking should be in done state.'
                )
                move_ids = order.picking_ids[0].move_ids
                self.assertEqual(
                    move_ids.mapped('state'),
                    ['done'] * len(move_ids),
                    'Move Lines should be in done state.'
                )

            # check account move in the invoiced order
            invoiced_order = self.pos_session.order_ids.filtered(lambda order: order.account_move)
            self.assertEqual(1, len(invoiced_order), 'Only one order is invoiced in this test.')

            # check account_move of orders before validating the session.
            self.assertTrue(invoiced_order.account_move, msg="Invoiced orders must have account_move.")
            uninvoiced_orders = self.pos_session.order_ids - invoiced_order
            self.assertTrue(
                all(not order.account_move for order in uninvoiced_orders),
                msg="Uninvoiced orders do not have account_move."
            )

        def _after_closing_cb():
            # check state of orders after validating the session.
            uninvoiced_orders = self.pos_session.order_ids.filtered(lambda order: not order.is_invoiced)
            self.assertTrue(
                all([order.state == 'done' for order in uninvoiced_orders]),  # noqa: C419
                msg="State should be 'done' for uninvoiced orders after validating the session."
            )

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 6), (self.product2, 3), (self.product3, 1)], 'payments': [(self.cash_pm1, 150)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product2, 20)], 'payments': [(self.bank_pm1, 410)], 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product3, 1)], 'payments': [(self.bank_pm1, 130)], 'is_invoiced': True, 'customer': self.customer, 'uuid': '00100-010-0003'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {
                '00100-010-0003': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 30, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 130, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 130), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 130, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 130, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'after_closing_cb': _after_closing_cb,
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 560, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 540, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 150, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 130, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((150, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 150, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 150, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((540, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 540, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 540, 'reconciled': True},
                        ]
                    }),
                ],
            },
        })

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

        def _before_closing_cb():
            # check values before closing the session
            self.assertEqual(2, self.pos_session.order_count)
            orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
            self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

            # return order
            order_to_return = self.pos_session.order_ids.filtered(lambda order: '12345-123-1234' in order.uuid)
            order_to_return.refund()
            refund_order = self.pos_session.order_ids.filtered(lambda order: order.state == 'draft')

            # check if amount to pay
            self.assertAlmostEqual(refund_order.amount_total - refund_order.amount_paid, -100)

            # pay the refund
            context_make_payment = {"active_ids": [refund_order.id], "active_id": refund_order.id}
            make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
                'payment_method_id': self.cash_pm1.id,
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
                    order.picking_ids[0].state,
                    'done',
                    'Picking should be in done state.'
                )
                move_ids = order.picking_ids[0].move_ids
                self.assertEqual(
                    move_ids.mapped('state'),
                    ['done'] * len(move_ids),
                    'Move Lines should be in done state.'
                )

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product2, 5)], 'payments': [(self.bank_pm1, 110)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 3), (self.product2, 2), (self.product3, 1)], 'payments': [(self.cash_pm1, 100)], 'uuid': '12345-123-1234'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 210, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 110, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((110, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 110, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 110, 'reconciled': True},
                        ]
                    }),
                ],
            },
        })

    def test_double_syncing_same_order(self):
        """ Test that double syncing the same order doesn't create duplicates records
        """
        self.open_new_session()
        # Create an order
        order_data = self.create_ui_order_data([(self.product1, 1)], payments=[(self.cash_pm1, 10)], customer=self.customer, is_invoiced=True)
        order_data['access_token'] = '0123456789'
        res = self.env['pos.order'].sync_from_ui([order_data])
        order_id = res['pos.order'][0]['id']
        # Sync the same order again
        res = self.env['pos.order'].sync_from_ui([order_data])
        order = self.env['pos.order'].browse(order_id)
        self.assertEqual(order.picking_count, 1, 'Order should have one picking')
