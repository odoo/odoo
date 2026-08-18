# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.point_of_sale.tests.test_pos_basic_config import TestPoSBasicConfig
from odoo.addons.pos_stock.tests.common import TestPosStockCommon

from dateutil.relativedelta import relativedelta


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

    def test_refund_ship_later_cancels_picking(self):
        self.config.write({
            'ship_later': True,
            'payment_method_ids': [(6, 0, self.cash_pm1.ids)],
        })
        self.open_new_session()

        shipping_date = fields.Date.today() + relativedelta(days=1)
        orders_map = self._create_orders([
            {
                'pos_order_lines_ui_args': [(self.product1, 2)],
                'payments': [(self.cash_pm1, 20)],
                'uuid': 'SHIP-LATER-REFUND',
                'customer': self.customer,
                'pos_order_ui_args': {
                    'shipping_date': fields.Date.to_string(shipping_date),
                },
            }
        ])
        order = orders_map['SHIP-LATER-REFUND']
        self.assertEqual(order.state, 'paid')
        self.assertTrue(order.picking_ids)
        self.assertTrue(order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')))

        refund_action = order.refund()
        refund_order = self.env['pos.order'].browse(refund_action['res_id'])
        payment_context = {"active_ids": [refund_order.id], "active_id": refund_order.id}
        make_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'payment_method_id': self.cash_pm1.id,
            'amount': -20,
        })
        make_payment.check()
        self.assertEqual(refund_order.state, 'paid')

        order._invalidate_cache()
        self.assertEqual(set(order.picking_ids.mapped('state')), {'cancel'})
        self.assertFalse(refund_order.picking_ids)

    def test_partial_refund_ship_later_reduces_picking(self):
        """Test that partial refunds before delivery reduce the picking quantities:
        - product1 (2 units): fully refunded → move cancelled
        - product2 (3 units): partially refunded (1 unit) → move qty reduced to 2
        - product3 (2 units): not refunded at all → move qty unchanged
        """
        self.config.write({
            'ship_later': True,
            'payment_method_ids': [(6, 0, self.cash_pm1.ids)],
        })
        self.open_new_session()

        shipping_date = fields.Date.today() + relativedelta(days=1)
        # product1: 2 * $10 = $20, product2: 3 * $20 = $60, product3: 2 * $30 = $60
        orders_map = self._create_orders([
            {
                'pos_order_lines_ui_args': [(self.product1, 2), (self.product2, 3), (self.product3, 2)],
                'payments': [(self.cash_pm1, 20 + 60 + 60)],
                'uuid': 'SHIP-LATER-PARTIAL',
                'customer': self.customer,
                'pos_order_ui_args': {
                    'shipping_date': fields.Date.to_string(shipping_date),
                },
            }
        ])
        order = orders_map['SHIP-LATER-PARTIAL']
        self.assertEqual(order.state, 'paid')
        self.assertTrue(order.picking_ids)

        # Verify initial move quantities
        picking = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        self.assertTrue(picking)
        product1_move = picking.move_ids.filtered(lambda m: m.product_id == self.product1)
        product2_move = picking.move_ids.filtered(lambda m: m.product_id == self.product2)
        product3_move = picking.move_ids.filtered(lambda m: m.product_id == self.product3)
        self.assertEqual(product1_move.product_uom_qty, 2.0)
        self.assertEqual(product2_move.product_uom_qty, 3.0)
        self.assertEqual(product3_move.product_uom_qty, 2.0)

        # Create refund order (starts as full refund of all lines)
        refund_action = order.refund()
        refund_order = self.env['pos.order'].browse(refund_action['res_id'])

        # Remove product3 from refund (not refunded at all)
        refund_order.lines.filtered(lambda l: l.product_id == self.product3).unlink()
        # Reduce product2 refund to 1 unit (partial refund, was -3)
        refund_order.lines.filtered(lambda l: l.product_id == self.product2).write({'qty': -1})
        refund_order._compute_prices()

        # product1: -2 * $10 = -$20, product2: -1 * $20 = -$20 → total refund = -$40
        payment_context = {"active_ids": [refund_order.id], "active_id": refund_order.id}
        make_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'payment_method_id': self.cash_pm1.id,
            'amount': -(20 + 20),
        })
        make_payment.check()
        self.assertEqual(refund_order.state, 'paid')

        order._invalidate_cache()
        picking._invalidate_cache()

        # Original picking should still exist and stay reserved (ready)
        self.assertEqual(picking.state, 'assigned')

        # product1 move should be completely removed (fully refunded, not just greyed out)
        self.assertFalse(
            picking.move_ids.filtered(lambda m: m.product_id == self.product1),
            "Fully-refunded move for product1 should be deleted from the picking."
        )

        # product2 move should be reduced from 3 to 2 (1 unit refunded)
        product2_move._invalidate_cache()
        self.assertEqual(product2_move.product_uom_qty, 2.0)
        self.assertIn(product2_move.state, ('draft', 'confirmed', 'assigned'))

        # product3 move should be unchanged (not refunded)
        product3_move._invalidate_cache()
        self.assertEqual(product3_move.product_uom_qty, 2.0)
        self.assertIn(product3_move.state, ('draft', 'confirmed', 'assigned'))

        # No return picking should be created since nothing was delivered
        self.assertFalse(refund_order.picking_ids)

    def test_partial_refund_ship_later_removes_fully_refunded_move(self):
        """Test that a fully-refunded move is completely removed from the picking
        (not left as a greyed-out/cancelled move).

        Scenario: buy 2x A + 1x B + 1x C, then cancel 1x A and 1x B.
        Expected picking: 1x A and 1x C — B should be gone entirely, not greyed out.
        """
        self.config.write({
            'ship_later': True,
            'payment_method_ids': [(6, 0, self.cash_pm1.ids)],
        })
        self.open_new_session()

        shipping_date = fields.Date.today() + relativedelta(days=1)
        # product1=A: 2 * $10 = $20, product2=B: 1 * $20 = $20, product3=C: 1 * $30 = $30
        orders_map = self._create_orders([
            {
                'pos_order_lines_ui_args': [(self.product1, 2), (self.product2, 1), (self.product3, 1)],
                'payments': [(self.cash_pm1, 20 + 20 + 30)],
                'uuid': 'SHIP-LATER-REMOVE-MOVE',
                'customer': self.customer,
                'pos_order_ui_args': {
                    'shipping_date': fields.Date.to_string(shipping_date),
                },
            }
        ])
        order = orders_map['SHIP-LATER-REMOVE-MOVE']
        self.assertEqual(order.state, 'paid')

        picking = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        self.assertTrue(picking)

        # Create refund: remove product3 (C) line → only refunding 1x A and 1x B
        refund_action = order.refund()
        refund_order = self.env['pos.order'].browse(refund_action['res_id'])
        refund_order.lines.filtered(lambda l: l.product_id == self.product3).unlink()
        # Reduce A refund to 1 unit
        refund_order.lines.filtered(lambda l: l.product_id == self.product1).write({'qty': -1})
        refund_order._compute_prices()

        # 1x A refund = -$10, 1x B refund = -$20 → total = -$30
        payment_context = {"active_ids": [refund_order.id], "active_id": refund_order.id}
        make_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'payment_method_id': self.cash_pm1.id,
            'amount': -(10 + 20),
        })
        make_payment.check()
        self.assertEqual(refund_order.state, 'paid')

        picking._invalidate_cache()

        # Picking should still be active (C not refunded)
        self.assertIn(picking.state, ('draft', 'confirmed', 'assigned'))

        # A (product1) move should be reduced to 1 unit
        product1_move = picking.move_ids.filtered(lambda m: m.product_id == self.product1 and m.state != 'cancel')
        self.assertEqual(len(product1_move), 1)
        self.assertEqual(product1_move.product_uom_qty, 1.0)

        # C (product3) move should be unchanged at 1 unit
        product3_move = picking.move_ids.filtered(lambda m: m.product_id == self.product3 and m.state != 'cancel')
        self.assertEqual(len(product3_move), 1)
        self.assertEqual(product3_move.product_uom_qty, 1.0)

        # B (product2) move should be completely removed — not just greyed out
        product2_move_all = picking.move_ids.filtered(lambda m: m.product_id == self.product2)
        self.assertFalse(
            product2_move_all,
            "Fully-refunded move for product2 (B) should be deleted from the picking, not left as a cancelled/greyed-out move."
        )

        # No return picking should be created
        self.assertFalse(refund_order.picking_ids)

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
