# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo import tools
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
        self.product99 = self.create_product('Product_99', self.categ_basic, 99, 50)
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
                move_lines = order.picking_ids[0].move_lines
                self.assertEqual(
                    move_lines.mapped('state'),
                    ['done'] * len(move_lines),
                    'Move Lines should be in done state.'
                )

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 5)], 'uid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product2, 7), (self.product3, 1)], 'uid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product3, 5), (self.product2, 3)], 'payments': [(self.bank_pm1, 220)], 'uid': '00100-010-0003'},
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
                move_lines = order.picking_ids[0].move_lines
                self.assertEqual(
                    move_lines.mapped('state'),
                    ['done'] * len(move_lines),
                    'Move Lines should be in done state.'
                )

            # check account move in the invoiced order
            invoiced_order = self.pos_session.order_ids.filtered(lambda order: order.account_move)
            self.assertEqual(1, len(invoiced_order), 'Only one order is invoiced in this test.')

            # check state of orders before validating the session.
            self.assertEqual('invoiced', invoiced_order.state, msg="state should be 'invoiced' for invoiced orders.")
            uninvoiced_orders = self.pos_session.order_ids - invoiced_order
            self.assertTrue(
                all([order.state == 'paid' for order in uninvoiced_orders]),
                msg="state should be 'paid' for uninvoiced orders before validating the session."
            )

        def _after_closing_cb():
            # check state of orders after validating the session.
            uninvoiced_orders = self.pos_session.order_ids.filtered(lambda order: not order.is_invoiced)
            self.assertTrue(
                all([order.state == 'done' for order in uninvoiced_orders]),
                msg="State should be 'done' for uninvoiced orders after validating the session."
            )

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 6), (self.product2, 3), (self.product3, 1), ], 'payments': [(self.cash_pm1, 150)], 'uid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product2, 20), ], 'payments': [(self.bank_pm1, 410)], 'uid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product3, 1), ], 'payments': [(self.bank_pm1, 130)], 'is_invoiced': True, 'customer': self.customer, 'uid': '00100-010-0003'},
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

    def test_orders_with_zero_valued_invoiced(self):
        """One invoiced order but with zero receivable line balance."""
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product0, 1)], 'payments': [(self.bank_pm1, 0)], 'customer': self.customer, 'is_invoiced': True, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {
                '00100-010-0001': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 0), False),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': False,
                'cash_statement': [],
                'bank_payments': [],
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
            order_to_return = self.pos_session.order_ids.filtered(lambda order: '12345-123-1234' in order.pos_reference)
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
                move_lines = order.picking_ids[0].move_lines
                self.assertEqual(
                    move_lines.mapped('state'),
                    ['done'] * len(move_lines),
                    'Move Lines should be in done state.'
                )

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product2, 5)], 'payments': [(self.bank_pm1, 110)], 'uid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 3), (self.product2, 2), (self.product3, 1)], 'payments': [(self.cash_pm1, 100)], 'uid': '12345-123-1234'},
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

    def test_split_cash_payments(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 5)], 'payments': [(self.cash_split_pm1, 100), (self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product2, 7), (self.product3, 1)], 'payments': [(self.cash_split_pm1, 70), (self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product3, 5), (self.product2, 3)], 'payments': [(self.cash_split_pm1, 120), (self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0003'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 590, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 300, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 70, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 120, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    }),
                    ((70, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 70, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 70, 'reconciled': True},
                        ]
                    }),
                    ((120, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 120, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 120, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((300, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 300, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 300, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_rounding_method(self):
        # set the cash rounding method
        self.config.cash_rounding = True
        self.config.rounding_method = self.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company['default_cash_difference_income_account_id'].copy().id,
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
            payments=[(self.bank_pm1, 429.90)]
        ))

        orders.append(self.create_ui_order_data(
            [(self.product1, 6), (self.product4, 4)],
            payments=[(self.bank_pm1, 99.85)]
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

    def test_correct_partner_on_invoice_receivables(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.cash_split_pm1 | self.bank_pm1 | self.bank_split_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.cash_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.cash_split_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uid': '00100-010-0003'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_split_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uid': '00100-010-0004'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.cash_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0005'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0006'},
                {'pos_order_lines_ui_args': [(self.product99, 1)], 'payments':[(self.cash_split_pm1, 99)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0007'},
                {'pos_order_lines_ui_args': [(self.product99, 1)], 'payments':[(self.bank_split_pm1, 99)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0008'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.other_customer, 'is_invoiced': True, 'uid': '00100-010-0009'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.other_customer, 'is_invoiced': True, 'uid': '00100-010-0010'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uid': '00100-010-0011'},
            ],
            'journal_entries_before_closing': {
                '00100-010-0001': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.cash_pm1, 100), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
                '00100-010-0002': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 100), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
                '00100-010-0003': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.cash_split_pm1, 100), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
                '00100-010-0004': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_split_pm1, 100), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
                '00100-010-0009': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 100), {
                            'line_ids': [
                                {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
                '00100-010-0010': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 100), {
                            'line_ids': [
                                {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
                '00100-010-0011': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 100), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 398, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 500, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 99, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 99, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 400, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    }),
                    ((99, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 99, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 99, 'reconciled': True},
                        ]
                    }),
                    ((200, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.bank_split_pm1.outstanding_account_id.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    }),
                    ((99, ), {
                        'line_ids': [
                            {'account_id': self.bank_split_pm1.outstanding_account_id.id, 'partner_id': self.customer.id, 'debit': 99, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 99, 'reconciled': True},
                        ]
                    }),
                    ((500, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 500, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 500, 'reconciled': True},
                        ]
                    }),
                ],
            },
        })

    def test_cash_register_if_no_order(self):
        # Process one order with product3
        self.open_new_session(0)
        session = self.pos_session
        order_data = self.create_ui_order_data([(self.product3, 1)])
        amount_paid = order_data['data']['amount_paid']
        self.env['pos.order'].create_from_ui([order_data])
        session.post_closing_cash_details(amount_paid)
        session.close_session_from_ui()

        cash_register = session.cash_register_id
        self.assertEqual(cash_register.balance_start, 0)
        self.assertEqual(cash_register.balance_end_real, amount_paid)

        # Open/Close session without any order in cash control
        self.open_new_session(amount_paid)
        session = self.pos_session
        session.post_closing_cash_details(amount_paid)
        session.close_session_from_ui()
        cash_register = session.cash_register_id
        self.assertEqual(cash_register.balance_start, amount_paid)
        self.assertEqual(cash_register.balance_end_real, amount_paid)
        self.assertEqual(self.config.last_session_closing_cash, amount_paid)

    def test_start_balance_with_two_pos(self):
        """ When having several POS with cash control, this tests ensures that each POS has its correct opening amount """

        def open_and_check(pos_data):
            self.config = pos_data['config']
            self.open_new_session()
            session = self.pos_session
            session.set_cashbox_pos(pos_data['amount_paid'], False)
            self.assertEqual(session.cash_register_id.balance_start, pos_data['amount_paid'])

        pos01_config = self.config
        pos02_config = pos01_config.copy()
        pos01_data = {'config': pos01_config, 'p_qty': 1, 'amount_paid': 0}
        pos02_data = {'config': pos02_config, 'p_qty': 3, 'amount_paid': 0}

        for pos_data in [pos01_data, pos02_data]:
            open_and_check(pos_data)
            session = self.pos_session

            order_data = self.create_ui_order_data([(self.product3, pos_data['p_qty'])])
            pos_data['amount_paid'] += order_data['data']['amount_paid']
            self.env['pos.order'].create_from_ui([order_data])

            session.post_closing_cash_details(pos_data['amount_paid'])
            session.close_session_from_ui()

        open_and_check(pos01_data)
        open_and_check(pos02_data)
