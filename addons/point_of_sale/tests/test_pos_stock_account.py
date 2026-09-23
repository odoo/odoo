# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSStock(TestPoSCommon):
    """ Tests for anglo saxon accounting scenario.
    """
    def setUp(self):
        super(TestPoSStock, self).setUp()

        self.config = self.basic_config
        self.product1 = self.create_product('Product 1', self.categ_anglo, 10.0, 5.0)
        self.product2 = self.create_product('Product 2', self.categ_anglo, 20.0, 10.0)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15.0)
        self.product4 = self.create_product('Product 4', self.categ_anglo, 10.0, 5.0)
        self.product4.type = 'consu'
        self.product4.is_storable = False
        # start inventory with 10 items for each product
        self.adjust_inventory([self.product1, self.product2, self.product3], [10, 10, 10])

        # change cost(standard_price) of anglo products
        # then set inventory from 10 -> 15
        self.product1.write({'standard_price': 6.0})
        self.product2.write({'standard_price': 6.0})
        self.adjust_inventory([self.product1, self.product2, self.product3], [15, 15, 15])

        # change cost(standard_price) of anglo products
        # then set inventory from 15 -> 25
        self.product1.write({'standard_price': 13.0})
        self.product2.write({'standard_price': 13.0})
        self.adjust_inventory([self.product1, self.product2, self.product3], [25, 25, 25])

        self.expense_account = self.categ_anglo.property_account_expense_categ_id
        self.valuation_account = self.categ_anglo.property_stock_valuation_account_id

    def test_01_orders_no_invoiced(self):
        """

        Orders
        ======
        +---------+----------+-----+-------------+------------+
        | order   | product  | qty | total price | total cost |
        +---------+----------+-----+-------------+------------+
        | order 1 | product1 |  10 |       100.0 |       50.0 |  -> 10 items at cost of 5.0 is consumed, remains 5 items at 6.0 and 10 items at 13.0
        |         | product2 |  10 |       200.0 |      100.0 |  -> 10 items at cost of 10.0 is consumed, remains 5 items at 6.0 and 10 items at 13.0
        +---------+----------+-----+-------------+------------+
        | order 2 | product2 |   7 |       140.0 |       56.0 |  -> 5 items at cost of 6.0 and 2 items at cost of 13.0, remains 8 items at cost of 13.0
        |         | product3 |   7 |       210.0 |        0.0 |
        +---------+----------+-----+-------------+------------+
        | order 3 | product1 |   6 |        60.0 |       43.0 |  -> 5 items at cost of 6.0 and 1 item at cost of 13.0, remains 9 items at cost of 13.0
        |         | product2 |   6 |       120.0 |       78.0 |  -> 6 items at cost of 13.0, remains 2 items at cost of 13.0
        |         | product3 |   6 |       180.0 |        0.0 |
        +---------+----------+-----+-------------+------------+
        | order 4 | product4 |   6 |        60.0 |        0.0 |  -> consumable product cost = 0
        +---------+----------+-----+-------------+------------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        | -1070.0 |
        | pos_receivable-cash |  1070.0 |
        | expense_account     |   327.0 |
        | output_account      |  -327.0 |
        +---------------------+---------+
        | Total balance       |    0.00 |
        +---------------------+---------+
        """

        def _before_closing_cb():
            # check values before closing the session
            self.assertEqual(4, self.pos_session.order_count)
            orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
            self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')
            self.assertAlmostEqual(orders_total, 1070.0, msg='The orders\'s total amount should equal the computed.')

            # check product qty_available after syncing the order
            self.assertEqual(self.product1.qty_available, 9)
            self.assertEqual(self.product2.qty_available, 2)
            self.assertEqual(self.product3.qty_available, 12)

            # picking and stock moves should be in done state
            for order in self.pos_session.order_ids:
                self.assertEqual(order.picking_ids[0].state, 'done', 'Picking should be in done state.')
                self.assertTrue(all(state == 'done' for state in order.picking_ids[0].move_ids.mapped('state')), 'Move Lines should be in done state.')

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 10)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product2, 7), (self.product3, 7)], 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 6), (self.product2, 6), (self.product3, 6)], 'uuid': '00100-010-0003'},
                {'pos_order_lines_ui_args': [(self.product4, 6)], 'uuid': '00100-010-0004'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 1070.0, 'reconciled': False},
                        {'account_id': self.expense_account.id, 'partner_id': False, 'debit': 327, 'credit': 0, 'reconciled': False},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 1070.0, 'credit': 0, 'reconciled': True},
                        {'account_id': self.valuation_account.id, 'partner_id': False, 'debit': 0, 'credit': 327, 'reconciled': False},
                    ],
                },
                'cash_statement': [
                    ((1070.0, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 1070.0, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 1070.0, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [],
            },
        })

    def test_02_orders_with_invoice(self):
        """

        Orders
        ======
        Same with test_01 but order 3 is invoiced.

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        |  -650.0 |
        | pos_receivable-cash |  1010.0 |
        | receivable          |  -360.0 |
        | expense_account     |   206.0 |
        | output_account      |  -206.0 |
        +---------------------+---------+
        | Total balance       |    0.00 |
        +---------------------+---------+
        """

        def _before_closing_cb():
            # check values before closing the session
            self.assertEqual(3, self.pos_session.order_count)
            orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
            self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')
            self.assertAlmostEqual(orders_total, 1010.0, msg='The orders\'s total amount should equal the computed.')

            # check product qty_available after syncing the order
            self.assertEqual(self.product1.qty_available, 9)
            self.assertEqual(self.product2.qty_available, 2)
            self.assertEqual(self.product3.qty_available, 12)

            # picking and stock moves should be in done state
            for order in self.pos_session.order_ids:
                self.assertEqual(order.picking_ids[0].state, 'done', 'Picking should be in done state.')
                self.assertTrue(all(state == 'done' for state in order.picking_ids[0].move_ids.mapped('state')), 'Move Lines should be in done state.')

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 10)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product2, 7), (self.product3, 7)], 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 6), (self.product2, 6), (self.product3, 6)], 'is_invoiced': True, 'customer': self.customer, 'uuid': '00100-010-0003'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {
                '00100-010-0003': {
                    'payments': [
                        ((self.cash_pm1, 360.0), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 360.0, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 360.0, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 650, 'reconciled': False},
                        {'account_id': self.expense_account.id, 'partner_id': False, 'debit': 206, 'credit': 0, 'reconciled': False},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 1010.0, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 360, 'reconciled': True},
                        {'account_id': self.valuation_account.id, 'partner_id': False, 'debit': 0, 'credit': 206, 'reconciled': False},
                    ],
                },
                'cash_statement': [
                    ((1010.0, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 1010.0, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 1010.0, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [],
            },
        })


    def test_03_order_product_w_owner(self):
        """
        Test order via POS a product having stock owner.
        """

        group_owner = self.env.ref('stock.group_tracking_owner')
        self.env.user.write({'group_ids': [(4, group_owner.id)]})
        self.product4 = self.create_product('Product 3', self.categ_basic, 30.0, 15.0)
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product4.id,
            'inventory_quantity': 10,
            'location_id': self.stock_location_components.id,
            'owner_id': self.partner_a.id,
        }).action_apply_inventory()

        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data([(self.product4, 1)]))

        # sync orders
        order = self.env['pos.order'].sync_from_ui(orders)

        # check values before closing the session
        self.assertEqual(1, self.pos_session.order_count)

        # check product qty_available after syncing the order
        self.assertEqual(self.product4.qty_available, 9)

        # picking and stock moves should be in done state
        for order in self.pos_session.order_ids:
            self.assertEqual(order.picking_ids[0].state, 'done', 'Picking should be in done state.')
            self.assertTrue(all(state == 'done' for state in order.picking_ids[0].move_ids.mapped('state')), 'Move Lines should be in done state.')
            self.assertTrue(self.partner_a == order.picking_ids[0].move_ids[0].move_line_ids[0].owner_id, 'Move Lines Owner should be taken into account.')

        # close the session
        self.pos_session.action_pos_session_validate()

    def test_04_order_refund(self):
        self.categ4 = self.env['product.category'].create({
            'name': 'Category 4',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })
        self.product4 = self.create_product('Product 4', self.categ4, 30.0, 15.0)

        self.open_new_session()
        orders = []
        orders.append(self.create_ui_order_data([(self.product4, 1)]))
        order = self.env['pos.order'].sync_from_ui(orders)

        refund_action = self.env['pos.order'].browse(order['pos.order'][0]['id']).refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_pm1.id,
        })
        refund_payment.with_context(**payment_context).check()

        self.pos_session.action_pos_session_validate()
        expense_account_move_line = self.env['account.move.line'].search([('account_id', '=', self.expense_account.id), ('product_id', '=', False)])
        self.assertEqual(expense_account_move_line.balance, 0.0, "Expense account should be 0.0")

    def test_stock_duplicate_warehouse_with_PoS_operation_type(self):
        wh = self.env['stock.warehouse'].create({
            'name': 'WH1',
            'code': 'WH1',
            'company_id': self.env.company.id,
        })
        wh_copy = wh.copy()
        self.assertTrue(wh_copy.pos_type_id)
        self.assertNotEqual(wh.pos_type_id, wh_copy.pos_type_id)

    def _sync_ui_orders(self, orders_data):
        """ Save orders through the same entry point as the POS UI and return them as a recordset. """
        result = self.env['pos.order'].sync_from_ui(orders_data)
        return self.env['pos.order'].browse([order['id'] for order in result['pos.order']])

    def _invoice_with_wizard(self, orders):
        """ Backend flow: Orders list > Action > Create invoice(s), i.e. the `pos.make.invoice` wizard. """
        self.env['pos.make.invoice'].with_context(active_ids=orders.ids).create({'consolidated_billing': True}).action_create_invoices()
        return orders.account_move

    def _get_cogs_balance(self, moves):
        return sum(moves.line_ids.filtered(lambda line: line.account_id == self.expense_account).mapped('balance'))

    def _create_two_customer_orders(self):
        """ Two orders of one product1 unit each for the same customer (FIFO cost 5.0 per unit). """
        return self._sync_ui_orders([
            self.create_ui_order_data([(self.product1, 1)], customer=self.customer),
            self.create_ui_order_data([(self.product1, 1)], customer=self.customer),
        ])

    def _assert_cogs_booked_once(self, orders, invoice):
        """ The COGS of the two invoiced units (10.0) must be booked exactly once over the invoice,
        the session closing entry and its per-order reversals. """
        self.assertEqual(len(invoice), 1, "The two orders of the same customer should be consolidated in one invoice")
        self.assertEqual(self._get_cogs_balance(invoice), 10.0, "The invoice should book the COGS of the two units")
        closing_reversals = self.env['account.move'].search([('reversed_pos_order_id', 'in', orders.ids)])
        self.assertEqual(
            self._get_cogs_balance(invoice | self.pos_session.move_id | closing_reversals), 10.0,
            "The COGS of the two invoiced units must be booked once over the invoice, the session closing entry and its reversals",
        )

    def test_05_cogs_invoice_wizard_before_closing_update_stock_at_closing(self):
        """ `action_pos_order_invoice` flags the order `to_invoice` and creates its own picking so
        that the closing entry skips it; the `pos.make.invoice` wizard does neither, so with "update
        quantities at session closing" the units are costed again by the closing entry. """
        self.env.company.point_of_sale_update_stock_quantities = 'closing'
        self.open_new_session()
        orders = self._create_two_customer_orders()
        invoice = self._invoice_with_wizard(orders)
        self.pos_session.action_pos_session_validate()
        self._assert_cogs_booked_once(orders, invoice)

    def test_06_cogs_invoice_wizard_after_closing_update_stock_at_closing(self):
        """ Invoicing after the closing: the orders have no own picking, so the automatic reversal of
        the closing entry carries no stock lines while the invoice books the COGS again. """
        self.env.company.point_of_sale_update_stock_quantities = 'closing'
        self.open_new_session()
        orders = self._create_two_customer_orders()
        self.pos_session.action_pos_session_validate()
        invoice = self._invoice_with_wizard(orders)
        self._assert_cogs_booked_once(orders, invoice)

    def test_07_cogs_invoice_wizard_before_closing_update_stock_in_real_time(self):
        """ Control: with the default real-time stock update each order owns its picking and the COGS
        is booked once. """
        self.env.company.point_of_sale_update_stock_quantities = 'real'
        self.open_new_session()
        orders = self._create_two_customer_orders()
        invoice = self._invoice_with_wizard(orders)
        self.pos_session.action_pos_session_validate()
        self._assert_cogs_booked_once(orders, invoice)

    def _sync_uninvoiced_refund(self, order):
        """ Refund one unit of `order` from the POS UI without ticking "Invoice". """
        refund_data = self.create_ui_order_data(
            [{'product': self.product1, 'quantity': -1, 'refunded_orderline_id': order.lines.id}],
            pos_order_ui_args={'is_refund': True},
            customer=self.customer,
        )
        # `sync_from_ui` also returns the refunded order: keep only the refund.
        return self._sync_ui_orders([refund_data]).filtered(lambda o: o.refunded_order_id == order)

    def _assert_refund_documented_by_credit_note(self, refund, invoice):
        self.assertEqual(len(refund), 1)
        self.assertTrue(refund.account_move, "An accepted refund of an invoiced order must be documented by a credit note")
        self.assertEqual(refund.account_move.move_type, 'out_refund')
        self.assertEqual(refund.account_move.reversed_entry_id, invoice, "The credit note must reverse the invoice of the refunded order")

    def test_08_uninvoiced_refund_of_order_invoiced_from_ui(self):
        """ The sale is documented by a posted customer invoice, so its refund must be documented by a
        credit note reversing that invoice. The server accepts the refund saved without invoicing, and
        its revenue and COGS land in the session closing entry without partner while the invoice stays
        paid. """
        self.open_new_session()
        order = self._sync_ui_orders([
            self.create_ui_order_data([(self.product1, 1)], customer=self.customer, is_invoiced=True),
        ])
        invoice = order.account_move
        self.assertEqual(invoice.state, 'posted')
        refund = self._sync_uninvoiced_refund(order)
        self._assert_refund_documented_by_credit_note(refund, invoice)

    def test_09_uninvoiced_refund_of_order_invoiced_with_wizard(self):
        """ Same as test_08 for an order invoiced with the `pos.make.invoice` wizard: it keeps
        `to_invoice` False, so the payment screen does not even propose to invoice the refund. """
        self.open_new_session()
        order = self._sync_ui_orders([
            self.create_ui_order_data([(self.product1, 1)], customer=self.customer),
        ])
        invoice = self._invoice_with_wizard(order)
        self.assertEqual(invoice.state, 'posted')
        refund = self._sync_uninvoiced_refund(order)
        self._assert_refund_documented_by_credit_note(refund, invoice)
