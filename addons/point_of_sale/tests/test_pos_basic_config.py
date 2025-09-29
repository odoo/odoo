# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo import fields
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import ValidationError
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import unittest.mock
from odoo.http import UserError


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
        self.product_multi_tax = self.create_product('Multi-tax product', self.categ_basic, 100, 100, (self.taxes['tax8'] | self.taxes['tax9']).ids)
        self.adjust_inventory([self.product1, self.product2, self.product3], [100, 50, 50])
        self.company_data_2 = self.setup_other_company()

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
                all([order.state == 'done' for order in uninvoiced_orders]),
                msg="State should be 'done' for uninvoiced orders after validating the session."
            )

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 6), (self.product2, 3), (self.product3, 1), ], 'payments': [(self.cash_pm1, 150)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product2, 20), ], 'payments': [(self.bank_pm1, 410)], 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product3, 1), ], 'payments': [(self.bank_pm1, 130)], 'is_invoiced': True, 'customer': self.customer, 'uuid': '00100-010-0003'},
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
                {'pos_order_lines_ui_args': [(self.product0, 1)], 'payments': [(self.bank_pm1, 0)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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

    def test_return_order_invoiced(self):

        def _before_closing_cb():
            order = self.pos_session.order_ids.filtered(lambda order: '666-666-666' in order.uuid)

            # refund
            order.refund()
            refund_order = self.pos_session.order_ids.filtered(lambda order: order.state == 'draft')

            # pay the refund
            context_make_payment = {"active_ids": [refund_order.id], "active_id": refund_order.id}
            make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
                'payment_method_id': self.cash_pm1.id,
                'amount': -100,
            })
            make_payment.check()

            # invoice refund
            refund_order.action_pos_order_invoice()

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments': [(self.cash_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '666-666-666'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {
                '666-666-666': {
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
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 0, 'reconciled': True},
                    ],
                },
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

    def test_split_cash_payments(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 5)], 'payments': [(self.cash_split_pm1, 100), (self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product2, 7), (self.product3, 1)], 'payments': [(self.cash_split_pm1, 70), (self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product3, 5), (self.product2, 3)], 'payments': [(self.cash_split_pm1, 120), (self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uuid': '00100-010-0003'},
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
        self.env['pos.order'].sync_from_ui(orders)

        self.assertEqual(orders[0]['amount_return'], 0, msg='The amount return should be 0')
        self.assertEqual(orders[1]['amount_return'], 0, msg='The amount return should be 0')

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
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.cash_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.cash_split_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0003'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_split_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0004'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.cash_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uuid': '00100-010-0005'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uuid': '00100-010-0006'},
                {'pos_order_lines_ui_args': [(self.product99, 1)], 'payments':[(self.cash_split_pm1, 99)], 'customer': self.customer, 'is_invoiced': False, 'uuid': '00100-010-0007'},
                {'pos_order_lines_ui_args': [(self.product99, 1)], 'payments':[(self.bank_split_pm1, 99)], 'customer': self.customer, 'is_invoiced': False, 'uuid': '00100-010-0008'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.other_customer, 'is_invoiced': True, 'uuid': '00100-010-0009'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.other_customer, 'is_invoiced': True, 'uuid': '00100-010-0010'},
                {'pos_order_lines_ui_args': [(self.product1, 10)], 'payments':[(self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0011'},
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
        amount_paid = order_data['amount_paid']
        with (
            self.assertLogs('odoo.addons.point_of_sale.models.pos_order', level='DEBUG') as cm,
            unittest.mock.patch('odoo.addons.point_of_sale.models.pos_order.randrange', return_value=1996)
        ):
            res = self.env['pos.order'].sync_from_ui([order_data])
            # Basic check for logs on order synchronization
            order_log_str = self.env['pos.order']._get_order_log_representation(order_data)
            odoo_order_id = res['pos.order'][0]['id']
            self.assertEqual(len(cm.output), 4)
            self.assertEqual(cm.output[0], f"INFO:odoo.addons.point_of_sale.models.pos_order:PoS synchronisation #1996 started for PoS orders references: [{order_log_str}]")
            self.assertTrue(cm.output[1].startswith(f'DEBUG:odoo.addons.point_of_sale.models.pos_order:PoS synchronisation #1996 processing order {order_log_str} order full data: '))
            self.assertEqual(cm.output[2], f'INFO:odoo.addons.point_of_sale.models.pos_order:PoS synchronisation #1996 order {order_log_str} created pos.order #{odoo_order_id}')
            self.assertEqual(cm.output[3], 'INFO:odoo.addons.point_of_sale.models.pos_order:PoS synchronisation #1996 finished')
            
        session.post_closing_cash_details(amount_paid)
        session.close_session_from_ui()

        self.assertEqual(session.cash_register_balance_start, 0)
        self.assertEqual(session.cash_register_balance_end_real, amount_paid)

        # Open/Close session without any order in cash control
        self.open_new_session(amount_paid)
        session = self.pos_session
        session.post_closing_cash_details(amount_paid)
        session.close_session_from_ui()
        self.assertEqual(session.cash_register_balance_start, amount_paid)
        self.assertEqual(session.cash_register_balance_end_real, amount_paid)
        self.assertEqual(self.config.last_session_closing_cash, amount_paid)

    def test_start_balance_with_two_pos(self):
        """ When having several POS with cash control, this tests ensures that each POS has its correct opening amount """

        def open_and_check(pos_data):
            self.config = pos_data['config']
            self.open_new_session(pos_data['amount_paid'])
            session = self.pos_session
            self.assertEqual(session.cash_register_balance_start, pos_data['amount_paid'])

        pos01_config = self.config
        self.cash_journal = self.env['account.journal'].create(
            {'name': 'CASH journal', 'type': 'cash', 'code': 'CSH00'})
        self.cash_payment_method = self.env['pos.payment.method'].create({
            'name': 'Cash Test',
            'journal_id': self.cash_journal.id,
            'receivable_account_id': pos01_config.payment_method_ids.filtered(lambda s: s.is_cash_count)[
                1].receivable_account_id.id
        })
        pos02_config = pos01_config.copy({
            'payment_method_ids': self.cash_payment_method
        })
        pos01_data = {'config': pos01_config, 'p_qty': 1, 'amount_paid': 0}
        pos02_data = {'config': pos02_config, 'p_qty': 3, 'amount_paid': 0}

        for pos_data in [pos01_data, pos02_data]:
            open_and_check(pos_data)
            session = self.pos_session

            order_data = self.create_ui_order_data([(self.product3, pos_data['p_qty'])])
            pos_data['amount_paid'] += order_data['amount_paid']
            self.env['pos.order'].sync_from_ui([order_data])

            session.post_closing_cash_details(pos_data['amount_paid'])
            session.close_session_from_ui()

        open_and_check(pos01_data)
        open_and_check(pos02_data)

    def test_pos_session_name_sequencing(self):
        """ This test check if the session name is correctly set according to the sequence """

        sequence = self.env['ir.sequence'].search([('code', '=', 'pos.session')])
        sequence.prefix = '/'
        sequence.write({'number_next_actual': 1000})
        name = self.config.name

        self.open_new_session(0)
        self.assertEqual(self.pos_session.name, name + '/01000')

        self.pos_session.close_session_from_ui()

        sequence.prefix = 'TEST/'

        self.open_new_session(0)
        self.assertEqual(self.pos_session.name, 'TEST/01001')

    def test_load_data_should_not_fail(self):
        """load_data shouldn't fail

        (Include test conditions here if possible)

        - When there are partners that belong to different company
        """

        # create a partner that belongs to different company
        company2 = self.company_data_2['company']
        self.env['res.partner'].create({
            'name': 'Test',
            'company_id': company2.id,
        })

        self.open_new_session()

        # calling load_data should not raise an error
        self.pos_session.load_data([])

    def test_invoice_past_refund(self):
        """ Test invoicing a past refund

        Orders
        ======
        +------------------+----------+-----------+----------+-----+-------+
        | order            | payments | invoiced? | product  | qty | total |
        +------------------+----------+-----------+----------+-----+-------+
        | order 1          | cash     | no        | product3 |   1 |    30 |
        +------------------+----------+-----------+----------+-----+-------+
        | order 2 (return) | cash     | no        | product3 |  -1 |   -30 |
        +------------------+----------+-----------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale (sales)        |     -30 |
        | sale (refund)       |      30 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """
        def _before_closing_cb():
            # Return the order
            order_to_return = self.pos_session.order_ids.filtered(lambda order: '12345-123-1234' in order.uuid)
            order_to_return.refund()
            refund_order = self.pos_session.order_ids.filtered(lambda order: order.state == 'draft')

            # Check if there's an amount to pay
            self.assertAlmostEqual(refund_order.amount_total - refund_order.amount_paid, -30)

            # Pay the refund
            context_make_payment = {"active_ids": [refund_order.id], "active_id": refund_order.id}
            make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
                'payment_method_id': self.cash_pm1.id,
                'amount': -30,
            })
            make_payment.check()

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product3, 1)], 'payments': [(self.cash_pm1, 30)], 'uuid': '12345-123-1234'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 30, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 30, 'credit': 0, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [],
            },
        })

        closed_session = self.pos_session
        self.assertTrue(closed_session.state == 'closed', 'Session should be closed.')

        return_to_invoice = closed_session.order_ids[1]
        test_customer = self.env['res.partner'].create({'name': 'Test Customer'})
        new_session_date = return_to_invoice.date_order + relativedelta(days=2)

        with freeze_time(new_session_date):
            # Create a new session after 2 days
            self.open_new_session(0)
            # Invoice the uninvoiced refund
            return_to_invoice.write({'partner_id': test_customer.id})
            return_to_invoice.action_pos_order_invoice()
            # Check the credit note
            self.assertTrue(return_to_invoice.account_move, 'Invoice should be created.')
            self.assertEqual(return_to_invoice.account_move.move_type, 'out_refund', 'Invoice should be a credit note.')
            self.assertEqual(return_to_invoice.account_move.invoice_date, new_session_date.date(), 'Invoice date should be the same as the session it is created in.')
            self.assertRecordValues(return_to_invoice.account_move, [{
                'amount_untaxed': 30,
                'amount_tax': 0,
                'amount_total': 30,
            }])
            self.assertRecordValues(return_to_invoice.account_move.line_ids, [
                {'account_id': self.sales_account.id, 'balance': 30},
                {'account_id': self.receivable_account.id, 'balance': -30},
            ])

    def test_invoice_past_order(self):
        # create 1 uninvoiced order then close the session
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product99, 1)], 'payments': [(self.bank_pm1, 99)], 'customer': False, 'is_invoiced': False, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 99, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 99, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((99, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 99, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 99, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

        # keep reference of the closed session
        closed_session = self.pos_session
        self.assertTrue(closed_session.state == 'closed', 'Session should be closed.')

        order_to_invoice = closed_session.order_ids[0]
        test_customer = self.env['res.partner'].create({'name': 'Test Customer'})

        with freeze_time(fields.Datetime.now() + relativedelta(days=2)):
            # create new session after 2 days
            self.open_new_session(0)
            # invoice the uninvoiced order
            order_to_invoice.write({'partner_id': test_customer.id})
            order_to_invoice.action_pos_order_invoice()
            # check invoice
            invoice = order_to_invoice.account_move
            self.assertTrue(invoice, 'Invoice should be created.')
            self.assertNotEqual(invoice.invoice_date, order_to_invoice.date_order.date(), 'Invoice date should not be the same as order date since the session was closed.')

            # check that the payment date is set to the order date which
            # is the real payment date and not to the invoice_date
            payment = invoice.line_ids.full_reconcile_id.reconciled_line_ids.move_id - invoice
            self.assertEqual(payment.date, order_to_invoice.date_order.date())

    def test_invoice_past_order_affecting_taxes(self):
        """ Test whether two taxes affecting each other don't trigger a recomputation on invoice generation
        """
        # Create 1 uninvoiced order then close the session
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product_multi_tax, 1)], 'payments': [(self.bank_pm1, 117.72)], 'customer': False, 'is_invoiced': False, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 8, 'reconciled': False},
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 9.72, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 117.72, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((117.72, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 117.72, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 117.72, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

        closed_session = self.pos_session
        self.assertTrue(closed_session.state == 'closed', 'Session should be closed.')

        order_to_invoice = closed_session.order_ids[0]
        test_customer = self.env['res.partner'].create({'name': 'Test Customer'})

        # Create a new session
        self.open_new_session(0)
        # Invoice the uninvoiced order
        order_to_invoice.write({'partner_id': test_customer.id})
        order_to_invoice.action_pos_order_invoice()
        # Check the invoice for the lines
        self.assertTrue(order_to_invoice.account_move, 'Invoice should be created.')
        self.assertRecordValues(order_to_invoice.account_move.line_ids, [
            {'account_id': self.sales_account.id, 'balance': -100, 'reconciled': False},
            {'account_id': self.tax_received_account.id, 'balance': -8, 'reconciled': False},
            {'account_id': self.tax_received_account.id, 'balance': -9.72, 'reconciled': False},
            {'account_id': self.receivable_account.id, 'balance': 117.72, 'reconciled': True},
        ])

    def test_limited_products_loading(self):
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.limited_product_count', 3)

        # Make the service products that are available in the pos inactive.
        # We don't need them to test the loading of 'consu' products.
        self.env['product.template'].search([('available_in_pos', '=', True), ('type', '=', 'service')]).write({'available_in_pos': False})

        session = self.open_new_session(0)
        self.product1.write({'company_id': False})
        self.product2.write({'company_id': False})
        self.product3.write({'company_id': False})

        def get_top_product_ids(count):
            data = session.load_data([])
            special_product = session.config_id._get_special_products().ids
            available_top_product = [product for product in data['product.template'] if product['product_variant_ids'][0] not in special_product]
            return [p['product_variant_ids'][0] for p in available_top_product[:count]]

        self.patch(self.env.cr, 'now', lambda: datetime.now() + timedelta(days=1))
        self.env['pos.order'].sync_from_ui([self.create_ui_order_data([(self.product1, 1)])])
        self.assertEqual(get_top_product_ids(1), [self.product1.id])

        self.patch(self.env.cr, 'now', lambda: datetime.now() + timedelta(days=2))
        self.env['pos.order'].sync_from_ui([self.create_ui_order_data([(self.product2, 1)])])
        self.assertEqual(get_top_product_ids(2), [self.product1.id, self.product2.id])

        self.patch(self.env.cr, 'now', lambda: datetime.now() + timedelta(days=3))
        self.env['pos.order'].sync_from_ui([self.create_ui_order_data([(self.product3, 1)])])
        self.assertEqual(get_top_product_ids(3), [self.product1.id, self.product2.id, self.product3.id])

    def test_closing_entry_by_product(self):
        # set the Group by Product at Closing Entry
        self.config.is_closing_entry_by_product = True
        self.open_new_session()

        # 4 orders

        # Orders
        # ======
        # +---------+----------+---------------+----------+-----+-------+
        # | order   | payments | invoiced?     | product  | qty | total |
        # +---------+----------+---------------+----------+-----+-------+
        # | order 1 | bank     | no            | product1 |   2 |    60 |
        # |         |          |               | product4 |   3 | 39.84 |
        # +---------+----------+---------------+----------+-----+-------+
        # | order 2 | bank     | yes           | product4 |   1 | 29.88 |
        # |         |          |               | product2 |   5 |   400 |
        # +---------+----------+---------------+----------+-----+-------+
        # | order 3 | bank     | yes           | product1 |   3 | 29.88 |
        # |         |          |               | product2 |  10 |   400 |
        # +---------+----------+---------------+----------+-----+-------+
        # | order 4 | bank     | yes           | product1 |   5 | 29.88 |
        # |         |          |               | product0 |  10|   400 |
        # +---------+----------+---------------+----------+-----+-------+

        # Expected Output
        # +---------------+-----------+
        # | invoice_line  | Quantity  |
        # +---------------+-----------+
        # | Product 0     |      10   |
        # +---------------+-----------+
        # | Product 1     |      10   |
        # +---------------+-----------+
        # | Product 2     |      15   |
        # +---------------+-----------+
        # | Product 4     |       4   |
        # +---------------+-----------+

        # create orders
        orders = []

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 2), (self.product4, 3)],
            payments=[(self.bank_pm1, 49.88)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product4, 1), (self.product2, 5)],
            payments=[(self.bank_pm1, 109.96)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 10)],
            payments=[(self.bank_pm1, 230)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product0, 10)],
            payments=[(self.bank_pm1, 50)]
        ))

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)
        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_account_move = self.pos_session.move_id

        # Define expected quantities for each product
        expected_product_quantity = {
            self.product0: 10,
            self.product1: 10,
            self.product2: 15,
            self.product4: 4,
        }
        # Iterate through invoice lines and assert the expected quantities
        for i in session_account_move.line_ids:
            if i.product_id and expected_product_quantity.get(i.product_id):
                self.assertEqual(i.quantity, expected_product_quantity.get(i.product_id), f"Unexpected quantity for {i.product_id.name}")

    def test_pos_payment_method_copy(self):
        """
        Test POS payment method copy:
            - Create two payment methods in which one of the payment method's journal type be cash
            - Copy multiple payment methods
            - Check the duplicated cash payment method journal should be empty
        """
        pm_1 = self.cash_pm1
        pm_2 = self.bank_pm1
        pm_3, pm_4 = (pm_1 + pm_2).copy()

        self.assertTrue(pm_3)
        self.assertFalse(pm_3.journal_id)
        self.assertTrue(pm_4)
        self.assertEqual(pm_4.journal_id.type, "bank")

    def test_single_config_global_invoice(self):
        """For a single POS config, create multiple orders and consolidate them into a single invoice"""
        self.open_new_session()
        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 2), (self.product4, 3)],
            payments=[(self.bank_pm1, 49.88)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product4, 1), (self.product2, 5)],
            payments=[(self.bank_pm1, 109.96)]
        ))

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)
        # close the session
        self.pos_session.action_pos_session_validate()

        pos_orders = self.env['pos.order'].search([])
        # set customer for the orders
        pos_orders.write({'partner_id': self.customer.id})

        # create consolidated invoice
        self.env['pos.make.invoice'].create({"consolidated_billing": True}).with_context({"active_ids": pos_orders.ids}).action_create_invoices()
        # check if have single invoice
        self.assertEqual(len(pos_orders), 2)
        self.assertEqual(len(pos_orders.account_move), 1)
        self.assertEqual(pos_orders.account_move.partner_id, self.customer)
        self.assertEqual(pos_orders.account_move.amount_total, sum(pos_orders.mapped('amount_total')))
        self.assertEqual(pos_orders.account_move.payment_state, 'paid')
        self.assertEqual(pos_orders.account_move.state, 'posted')

    def test_multi_config_global_invoice(self):
        self.open_new_session()
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 10)],
            payments=[(self.bank_pm1, 230)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product0, 10)],
            payments=[(self.bank_pm1, 50)]
        ))
        self.env['pos.order'].sync_from_ui(orders)
        self.pos_session.action_pos_session_validate()

        # open new session & create orders
        self.open_new_session()
        orders2 = []
        orders2.append(self.create_ui_order_data(
            [(self.product1, 2), (self.product4, 3)],
            payments=[(self.bank_pm1, 49.88)]
        ))
        orders2.append(self.create_ui_order_data(
            [(self.product4, 1), (self.product2, 5)],
            payments=[(self.bank_pm1, 109.96)]
        ))
        self.env['pos.order'].sync_from_ui(orders2)
        self.pos_session.action_pos_session_validate()

        pos_orders = self.env['pos.order'].search([])
        # set customer for the orders
        pos_orders.write({'partner_id': self.customer.id})

        # create consolidated invoice
        self.env['pos.make.invoice'].create({"consolidated_billing": True}).with_context({"active_ids": pos_orders.ids}).action_create_invoices()
        # check if have single invoice
        self.assertEqual(len(pos_orders), 4)
        self.assertEqual(len(pos_orders.account_move), 1)
        self.assertEqual(pos_orders.account_move.partner_id, self.customer)
        self.assertEqual(pos_orders.account_move.amount_total, round(sum(pos_orders.mapped('amount_total')), 2))
        self.assertEqual(pos_orders.account_move.payment_state, 'paid')
        self.assertEqual(pos_orders.account_move.state, 'posted')

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
        self.assertEqual(res['pos.order'][0]['id'], order_id, 'Syncing the same order should not create a new one')

        order = self.env['pos.order'].browse(order_id)
        self.assertEqual(order.picking_count, 1, 'Order should have one picking')
        self.assertEqual(len(order.payment_ids), 1, 'Order should have one payment')
        self.assertEqual(self.env['account.move'].search_count([('pos_order_ids', 'in', order.ids)]), 1, 'Order should have one invoice')

    def test_pos_archived_combination(self):
        product = self.env['product.template'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
        })

        attribute_1, attribute_2, attribute_3 = self.env['product.attribute'].create([{
            'name': 'Attribute 1',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }, {
            'name': 'Attribute 2',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }, {
            'name': 'Attribute 3',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }])

        _, _, ptal = self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product.id,
            'attribute_id': attribute_1.id,
            'value_ids': [(6, 0, attribute_1.value_ids.ids)],
            'sequence': 3,
        }, {
            'product_tmpl_id': product.id,
            'attribute_id': attribute_2.id,
            'value_ids': [(6, 0, attribute_2.value_ids.ids)],
            'sequence': 2,
        }, {
            'product_tmpl_id': product.id,
            'attribute_id': attribute_3.id,
            'value_ids': [(6, 0, attribute_3.value_ids.ids)],
            'sequence': 1,
        }])

        product.write({
            'attribute_line_ids': [(2, ptal.id)],
        })

        self.open_new_session()
        response = self.pos_session.load_data([])
        product_data = next((item for item in response['product.template'] if item['id'] == product.id), None)

        self.assertEqual(len(product_data['_archived_combinations']), 0, "There should be no archived combinations for the product")

        first_variant = product.product_variant_ids[0]
        first_variant.write({'active': False})

        response = self.pos_session.load_data([])
        product_data = next((item for item in response['product.template'] if item['id'] == product.id), None)

        self.assertEqual(len(product_data['_archived_combinations']), 1, "There should be one archived combination for the product")
        self.assertEqual(len(product_data['_archived_combinations'][0]), 2, "Archived combination should have two values")
        self.assertTrue(all(value in product_data['_archived_combinations'][0] for value in first_variant.product_template_attribute_value_ids.ids), "Archived combination should match the first variant's attribute values")

    def test_refunded_order_id(self):
        """
        An order containing refunded lines from two different orders is no longer allowed,
        but some legacy records of this kind may still exist.
        This test ensures that the refunded_order_id is correctly computed in such cases.
        """
        current_session = self.open_new_session()
        orders = list(self._create_orders([
            {'pos_order_lines_ui_args': [(self.product1, 1)]},
            {'pos_order_lines_ui_args': [(self.product2, 1)]}
        ]).values())

        refund_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'lines': [
                (0, 0, {
                    'product_id': self.product1.id,
                    'price_unit': -10,
                    'qty': 1,
                    'tax_ids': [[6, False, []]],
                    'price_subtotal': -10,
                    'price_subtotal_incl': -10,
                    'refunded_orderline_id': orders[0].lines[0].id
                }),
                (0, 0, {
                    'product_id': self.product2.id,
                    'price_unit': -10,
                    'qty': 1,
                    'tax_ids': [[6, False, []]],
                    'price_subtotal': -10,
                    'price_subtotal_incl': -10,
                    'refunded_orderline_id': orders[1].lines[0].id
                })
            ],
            'amount_paid': -10,
            'amount_total': -10,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })

        self.assertEqual(refund_order.refunded_order_id, orders[0])

    def test_cannot_archive_journal_linked_to_pos_payment_method(self):
        """Test that archiving a journal linked to a POS payment method is blocked, and allowed when not linked."""

        test_journal = self.env['account.journal'].create({
            'name': 'Test POS Journal',
            'type': 'cash',
            'code': 'TPJ',
            'company_id': self.env.company.id,
        })
        test_payment_method = self.env['pos.payment.method'].create({
            'name': 'Test PM',
            'journal_id': test_journal.id,
            'receivable_account_id': self.cash_pm1.receivable_account_id.id,
        })

        with self.assertRaises(ValidationError):
            test_journal.action_archive()

        # Unlink the payment method and try again (should succeed)
        test_payment_method.journal_id = False
        test_journal.action_archive()
        self.assertFalse(test_journal.active, "Journal should be archived when not linked to a POS payment method.")

    def test_archive_delete_special_product(self):
        special_product = self.env.ref('point_of_sale.product_product_tip')
        with self.assertRaisesRegex(UserError, "You cannot archive a product that is set as a special product in a Point of Sale configuration. Please change the configuration first."):
            special_product.action_archive()
        with self.assertRaisesRegex(UserError, "You cannot archive a product that is set as a special product in a Point of Sale configuration. Please change the configuration first."):
            special_product.product_variant_ids[0].action_archive()
        with self.assertRaisesRegex(UserError, "You cannot archive a product that is set as a special product in a Point of Sale configuration. Please change the configuration first."):
            special_product.unlink()
        with self.assertRaisesRegex(UserError, "You cannot archive a product that is set as a special product in a Point of Sale configuration. Please change the configuration first."):
            special_product.product_variant_ids[0].unlink()
