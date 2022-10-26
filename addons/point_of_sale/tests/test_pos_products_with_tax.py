# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools

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
        self.product4 = self.create_product(
            'Product 4',
            self.categ_basic,
            54.99,
            tax_ids=[self.taxes['tax_fixed006'].id, self.taxes['tax_fixed012'].id, self.taxes['tax21'].id],
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

        def _before_closing_cb():
            # check values before closing the session
            self.assertEqual(3, self.pos_session.order_count)
            orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
            self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, 'Total order amount should be equal to the total payment amount.')

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 5)], 'uid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product2, 7), (self.product3, 4)], 'uid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 1), (self.product3, 5), (self.product2, 3)], 'payments': [(self.bank_pm1, 230.25)], 'uid': '00100-010-0003'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 24.89, 'reconciled': False},
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 51.82, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 110, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 272.73, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 245.45, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 230.25, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 474.64, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((474.64, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 474.64, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 474.64, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((230.25, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 230.25, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 230.25, 'reconciled': True},
                        ]
                    }),
                ],
            },
        })

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

        def _before_closing_cb():
            # check values before closing the session
            self.assertEqual(4, self.pos_session.order_count)
            orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
            self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

            # check account move in the invoiced order
            invoiced_orders = self.pos_session.order_ids.filtered(lambda order: order.is_invoiced)
            self.assertEqual(2, len(invoiced_orders), 'Only one order is invoiced in this test.')
            invoices = invoiced_orders.mapped('account_move')
            self.assertAlmostEqual(sum(invoices.mapped('amount_total')), 481.08)

        def _after_closing_cb():
            session_move = self.pos_session.move_id
            tax_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)

            manually_calculated_taxes = (-6.81, -44.54)
            self.assertAlmostEqual(sum(manually_calculated_taxes), sum(tax_lines.mapped('balance')))
            for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
                self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined.')

            base_amounts = (97.27, 445.46)  # computation does not include invoiced order.
            self.assertAlmostEqual(sum(base_amounts), sum(tax_lines.mapped('tax_base_amount')))

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product3, 1), (self.product1, 6), (self.product2, 3)], 'uid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product2, 20), (self.product1, 1)], 'payments': [(self.bank_pm1, 410.7)], 'uid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product3, 10)], 'payments': [(self.bank_pm1, 426.09)], 'customer': self.customer, 'is_invoiced': True, 'uid': '09876-098-0987'},
                {'pos_order_lines_ui_args': [(self.product4, 1)], 'payments': [(self.bank_pm1, 54.99)], 'customer': self.customer, 'is_invoiced': True, 'uid': '00100-010-0004'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {
                '09876-098-0987': {
                    'payments': [
                        ((self.bank_pm1, 426.09), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 426.09, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 426.09, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
                '00100-010-0004': {
                    'payments': [
                        ((self.bank_pm1, 54.99), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 54.99, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 54.99, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
            },
            'after_closing_cb': _after_closing_cb,
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 6.81, 'reconciled': False},
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 44.54, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 27.27, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 70, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 418.19, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 891.78, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 156.11, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 481.08, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((156.11, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 156.11, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 156.11, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((891.78, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 891.78, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 891.78, 'reconciled': True},
                        ]
                    }),
                ],
            },
        })

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

        def _before_closing_cb():
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
                'payment_method_id': self.cash_pm1.id,
                'amount': -104.01,
            })
            make_payment.check()
            self.assertEqual(refund_order.state, 'paid', 'Payment is registered, order should be paid.')
            self.assertAlmostEqual(refund_order.amount_paid, -104.01, msg='Amount paid for return order should be negative.')

        def _after_closing_cb():
            manually_calculated_taxes = (4.01, 6.37)  # should be positive since it is return order
            tax_lines = self.pos_session.move_id.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)
            self.assertAlmostEqual(sum(manually_calculated_taxes), sum(tax_lines.mapped('balance')))
            for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
                self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined and should be debit.')

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 3), (self.product2, 2), (self.product3, 1)], 'payments': [(self.cash_pm1, 104.01)], 'customer': self.customer, 'is_invoiced': True, 'uid': '12345-123-1234'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {
                '12345-123-1234': {
                    'payments': [
                        ((self.cash_pm1, 104.01), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 104.01, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 104.01, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
            },
            'after_closing_cb': _after_closing_cb,
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 4.01, 'credit': 0, 'reconciled': False},
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 6.37, 'credit': 0, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 30, 'credit': 0, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 36.36, 'credit': 0, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 27.27, 'credit': 0, 'reconciled': False},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 104.01, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [],
            },
        })

    def test_pos_create_correct_account_move(self):
        """ Test for orders with global rounding disabled

        Orders
        ======
        +---------+----------+-----------+----------+------+----------+------------------+--------+
        | order   | payments | invoiced? | product  | qty  |  untaxed | tax              |  total |
        +---------+----------+-----------+----------+------+----------+------------------+--------+
        | order 1 | cash     | no        | product1 |    1 |     10.0 |  2.10            |  12.10 |
        |         |          |           | product2 |   -1 |     -5.0 | -1.05            |  -6.05 |
        +---------+----------+-----------+----------+------+----------+------------------+--------+
        """
        tax_21_incl = self.taxes['tax21']
        product1 = self.create_product(
            name='Product 1',
            category=self.categ_basic,
            lst_price=12.10,
            tax_ids=tax_21_incl.ids,
        )
        product2 = self.create_product(
            name='Product 2',
            category=self.categ_basic,
            lst_price=6.05,
            tax_ids=tax_21_incl.ids,
        )
        self.open_new_session()
        self.env['pos.order'].create_from_ui([self.create_ui_order_data([
            (product1, 1),
            (product2, -1),
        ])])
        self.pos_session.action_pos_session_validate()

        lines = self.pos_session.move_id.line_ids.sorted('balance')
        self.assertEqual(2, len(lines.filtered(lambda l: l.tax_ids)), "Taxes should have been set on 2 lines")
        self.assertEqual(4, len(lines.filtered(lambda l: l.tax_tag_ids)), "Tags should have been set on 4 lines")
        self.assertRecordValues(lines, [
            # pylint: disable=bad-whitespace
            {'account_id': self.sale_account.id,                   'balance': -10.0, 'tax_ids': tax_21_incl.ids, 'tax_tag_ids': self.tax_tag_invoice_base.ids},
            {'account_id': self.tax_received_account.id,           'balance': -2.10, 'tax_ids': [],              'tax_tag_ids': self.tax_tag_invoice_tax.ids},
            {'account_id': self.tax_received_account.id,           'balance':  1.05, 'tax_ids': [],              'tax_tag_ids': self.tax_tag_refund_tax.ids},
            {'account_id': self.sale_account.id,                   'balance':  5.00, 'tax_ids': tax_21_incl.ids, 'tax_tag_ids': self.tax_tag_refund_base.ids},
            {'account_id': self.cash_pm1.receivable_account_id.id, 'balance':  6.05, 'tax_ids': [],              'tax_tag_ids': []},
        ])

    def test_pos_create_account_move_round_globally(self):
        """ Test for orders with global rounding enabled

        Orders
        ======
        +---------+----------+-----------+----------+------+----------+------------------+--------+
        | order   | payments | invoiced? | product  | qty  |  untaxed | tax              |  total |
        +---------+----------+-----------+----------+------+----------+------------------+--------+
        | order 1 | cash     | no        | product1 |    1 |     10.0 |  2.10            |  12.10 |
        |         |          |           | product2 |   -1 |     -5.0 | -1.05            |  -6.05 |
        +---------+----------+-----------+----------+------+----------+------------------+--------+
        """
        tax_21_incl = self.taxes['tax21']
        tax_21_incl.company_id.tax_calculation_rounding_method = 'round_globally'

        product1 = self.create_product(
            name='Product 1',
            category=self.categ_basic,
            lst_price=12.10,
            tax_ids=tax_21_incl.ids,
        )
        product2 = self.create_product(
            name='Product 2',
            category=self.categ_basic,
            lst_price=6.05,
            tax_ids=tax_21_incl.ids,
        )
        self.open_new_session()
        self.env['pos.order'].create_from_ui([self.create_ui_order_data([
            (product1, 1),
            (product2, -1),
        ])])
        self.pos_session.action_pos_session_validate()

        lines = self.pos_session.move_id.line_ids.sorted('balance')
        self.assertEqual(2, len(lines.filtered(lambda l: l.tax_ids)), "Taxes should have been set on 2 lines")
        self.assertEqual(4, len(lines.filtered(lambda l: l.tax_tag_ids)), "Tags should have been set on 4 lines")
        self.assertRecordValues(lines, [
            # pylint: disable=bad-whitespace
            {'account_id': self.sale_account.id,                   'balance': -10.0, 'tax_ids': tax_21_incl.ids, 'tax_tag_ids': self.tax_tag_invoice_base.ids},
            {'account_id': self.tax_received_account.id,           'balance': -2.10, 'tax_ids': [],              'tax_tag_ids': self.tax_tag_invoice_tax.ids},
            {'account_id': self.tax_received_account.id,           'balance':  1.05, 'tax_ids': [],              'tax_tag_ids': self.tax_tag_refund_tax.ids},
            {'account_id': self.sale_account.id,                   'balance':  5.00, 'tax_ids': tax_21_incl.ids, 'tax_tag_ids': self.tax_tag_refund_base.ids},
            {'account_id': self.cash_pm1.receivable_account_id.id, 'balance':  6.05, 'tax_ids': [],              'tax_tag_ids': []},
        ])

    def test_pos_create_correct_account_move_round_globally_discount(self):
        """ Test for orders with global rounding enabled

        Orders
        ======
        +---------+----------+------+----------+------+---------------------+-----------+---------------------------+---------+--------+--------+
        | order   | payments | inv? | product  | qty  | original price unit | Discount  | price unit after discount | untaxed | tax    |  total |
        +---------+----------+------+----------+------+---------------------+-----------+---------------------------+---------+--------+--------+
        | order 1 | cash     | no   | product1 |    1 |               12.10 |        5% |                     10.89 |    9.00 |   1.89 |  10.89 |
        |         |          |      | product2 |   -1 |                6.05 |        5% |                      5.45 |   -4.50 |  -0.95 | -5.445 |
        +---------+----------+------+----------+------+---------------------+-----------+---------------------------+---------+--------+--------+
        """
        tax_21_incl = self.taxes['tax21']
        tax_21_incl.company_id.tax_calculation_rounding_method = 'round_globally'

        product1 = self.create_product(
            name='Product 1',
            category=self.categ_basic,
            lst_price=12.10,
            tax_ids=tax_21_incl.ids,
        )
        product2 = self.create_product(
            name='Product 2',
            category=self.categ_basic,
            lst_price=6.05,
            tax_ids=tax_21_incl.ids,
        )
        self.open_new_session()
        self.env['pos.order'].create_from_ui([self.create_ui_order_data([
            (product1, 1, 10),
            (product2, -1, 10),
        ])])
        self.pos_session.action_pos_session_validate()

        lines = self.pos_session.move_id.line_ids.sorted('balance')

        self.assertEqual(2, len(lines.filtered(lambda l: l.tax_ids)), "Taxes should have been set on 2 lines")
        self.assertEqual(4, len(lines.filtered(lambda l: l.tax_tag_ids)), "Tags should have been set on 4 lines")
        self.assertRecordValues(lines, [
            # pylint: disable=bad-whitespace
            {'account_id': self.sale_account.id,                   'balance': - 9.0, 'tax_ids': tax_21_incl.ids, 'tax_tag_ids': self.tax_tag_invoice_base.ids},
            {'account_id': self.tax_received_account.id,           'balance': -1.89, 'tax_ids': [],              'tax_tag_ids': self.tax_tag_invoice_tax.ids},
            {'account_id': self.tax_received_account.id,           'balance':  0.95, 'tax_ids': [],              'tax_tag_ids': self.tax_tag_refund_tax.ids},
            {'account_id': self.sale_account.id,                   'balance':   4.5, 'tax_ids': tax_21_incl.ids, 'tax_tag_ids': self.tax_tag_refund_base.ids},
            {'account_id': self.cash_pm1.receivable_account_id.id, 'balance':  5.44, 'tax_ids': [],              'tax_tag_ids': []},
        ])

    def test_pos_create_correct_account_move_round_globally_discount_real_use_case(self):
        """ Test for orders with global rounding enabled

        Orders
        ======
        +---------+----------+------+----------+------+---------------------+-----------+---------------------------+---------+--------+--------+
        | order   | payments | inv? | product  | qty  | original price unit | Discount  | price unit after discount | untaxed | tax    |  total |
        +---------+----------+------+----------+------+---------------------+-----------+---------------------------+---------+--------+--------+
        | order 1 | cash     | no   | product1 |    6 |               11.80 |        5% |                     11.21 |   55.59 |  11.67 |  67.26 |
        |         |          |      | product2 |   -6 |               15.30 |        5% |                    14.535 |  -72.07 | -15.14 | -87.21 |
        +---------+----------+------+----------+------+---------------------+-----------+---------------------------+---------+--------+--------+
        """
        tax_21_incl = self.taxes['tax21']
        tax_21_incl.company_id.tax_calculation_rounding_method = 'round_globally'

        product1 = self.create_product(
            name='Product 1',
            category=self.categ_basic,
            lst_price=11.80,
            tax_ids=tax_21_incl.ids,
        )
        product2 = self.create_product(
            name='Product 2',
            category=self.categ_basic,
            lst_price=15.30,
            tax_ids=tax_21_incl.ids,
        )
        self.open_new_session()
        self.env['pos.order'].create_from_ui([self.create_ui_order_data([
            (product1, 6, 5),
            (product2, -6, 5),
        ])])
        self.pos_session.action_pos_session_validate()

        lines = self.pos_session.move_id.line_ids.sorted('balance')

        self.assertEqual(2, len(lines.filtered(lambda l: l.tax_ids)), "Taxes should have been set on 2 lines")
        self.assertEqual(4, len(lines.filtered(lambda l: l.tax_tag_ids)), "Tags should have been set on 4 lines")
        self.assertRecordValues(lines, [
            # pylint: disable=bad-whitespace
            {'account_id': self.sale_account.id,                   'balance': -55.59, 'tax_ids': tax_21_incl.ids, 'tax_tag_ids': self.tax_tag_invoice_base.ids},
            {'account_id': self.cash_pm1.receivable_account_id.id, 'balance': -19.95, 'tax_ids': [],              'tax_tag_ids': []},
            {'account_id': self.tax_received_account.id,           'balance': -11.67, 'tax_ids': [],              'tax_tag_ids': self.tax_tag_invoice_tax.ids},
            {'account_id': self.tax_received_account.id,           'balance':  15.14, 'tax_ids': [],              'tax_tag_ids': self.tax_tag_refund_tax.ids},
            {'account_id': self.sale_account.id,                   'balance':  72.07, 'tax_ids': tax_21_incl.ids, 'tax_tag_ids': self.tax_tag_refund_base.ids},
        ])

    def test_fixed_tax_positive_qty(self):

        fixed_tax = self.env['account.tax'].create({
            'name': 'fixed amount tax',
            'amount_type': 'fixed',
            'amount': 1,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, self.tax_tag_invoice_base.ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': self.tax_received_account.id,
                    'tag_ids': [(6, 0, self.tax_tag_invoice_tax.ids)],
                }),
            ],
        })

        zero_amount_product = self.env['product.product'].create({
            'name': 'Zero Amount Product',
            'available_in_pos': True,
            'list_price': 0,
            'taxes_id': [(6, 0, [fixed_tax.id])],
        })

        self.open_new_session()
        self.env['pos.order'].create_from_ui([self.create_ui_order_data([
            (zero_amount_product, 1),
        ])])
        self.pos_session.action_pos_session_validate()

        lines = self.pos_session.move_id.line_ids.sorted('balance')

        self.assertRecordValues(lines, [
            {'account_id': self.tax_received_account.id, 'balance': -1},
            {'account_id': self.sale_account.id, 'balance': 0},
            {'account_id': self.cash_pm1.receivable_account_id.id, 'balance': 1},
        ])
