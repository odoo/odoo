# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import skip

import odoo

from odoo import tools
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSOtherCurrencyConfig(TestPoSCommon):
    """ Test PoS with basic configuration
    """

    def setUp(self):
        super(TestPoSOtherCurrencyConfig, self).setUp()

        self.config = self.other_currency_config
        self.product1 = self.create_product('Product 1', self.categ_basic, 10.0, 5)
        self.product2 = self.create_product('Product 2', self.categ_basic, 20.0, 10)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15)
        self.product4 = self.create_product('Product 4', self.categ_anglo, 100, 50)
        self.product5 = self.create_product('Product 5', self.categ_anglo, 200, 70)
        self.product6 = self.create_product('Product 6', self.categ_anglo, 45.3, 10.73)
        self.product7 = self.create_product('Product 7', self.categ_basic, 7, 7, tax_ids=self.taxes['tax7'].ids)
        self.adjust_inventory(
            [self.product1, self.product2, self.product3, self.product4, self.product5, self.product6, self.product7],
            [100, 50, 50, 100, 100, 100, 100]
        )
        # change the price of product2 to 12.99 fixed. No need to convert.
        pricelist_item = self.env['product.pricelist.item'].create({
            'product_tmpl_id': self.product2.product_tmpl_id.id,
            'fixed_price': 12.99,
        })
        self.config.pricelist_id.write({'item_ids': [(6, 0, (self.config.pricelist_id.item_ids | pricelist_item).ids)]})

        self.expense_account = self.categ_anglo.property_account_expense_categ_id

    def test_01_check_product_cost(self):
        # Product price should be half of the original price because currency rate is 0.5.
        # (see `self._create_other_currency_config` method)
        # Except for product2 where the price is specified in the pricelist.

        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product1, 1), 5.00)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product2, 1), 12.99)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product3, 1), 15.00)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product4, 1), 50)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product5, 1), 100)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product6, 1), 22.65)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product7, 1), 3.50)

    def test_02_orders_without_invoice(self):
        """ orders without invoice

        Orders
        ======
        +---------+----------+-----------+----------+-----+-------+
        | order   | payments | invoiced? | product  | qty | total |
        +---------+----------+-----------+----------+-----+-------+
        | order 1 | cash     | no        | product1 |  10 |    50 |
        |         |          |           | product2 |  10 | 129.9 |
        |         |          |           | product3 |  10 |   150 |
        +---------+----------+-----------+----------+-----+-------+
        | order 2 | cash     | no        | product1 |   5 |    25 |
        |         |          |           | product2 |   5 | 64.95 |
        +---------+----------+-----------+----------+-----+-------+
        | order 3 | bank     | no        | product2 |   5 | 64.95 |
        |         |          |           | product3 |   5 |    75 |
        +---------+----------+-----------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+-----------------+
        | account             | balance | amount_currency |
        +---------------------+---------+-----------------+
        | sale_account        | -1119.6 |         -559.80 |
        | pos receivable bank |   279.9 |          139.95 |
        | pos receivable cash |   839.7 |          419.85 |
        +---------------------+---------+-----------------+
        | Total balance       |     0.0 |            0.00 |
        +---------------------+---------+-----------------+
        """

        def _before_closing_cb():
            # check values before closing the session
            self.assertEqual(3, self.pos_session.order_count)
            orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
            self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        self._run_test({
            'payment_methods': self.cash_pm2 | self.bank_pm2,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 10), (self.product3, 10)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 5), (self.product2, 5)], 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product2, 5), (self.product3, 5)], 'payments': [(self.bank_pm2, 139.95)], 'uuid': '00100-010-0003'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 1119.6, 'reconciled': False, 'amount_currency': -559.80},
                        {'account_id': self.bank_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 279.9, 'credit': 0, 'reconciled': True, 'amount_currency': 139.95},
                        {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 839.7, 'credit': 0, 'reconciled': True, 'amount_currency': 419.85},
                    ],
                },
                'cash_statement': [
                    ((419.85, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm2.journal_id.default_account_id.id, 'partner_id': False, 'debit': 839.7, 'credit': 0, 'reconciled': False, 'amount_currency': 419.85},
                            {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 839.7, 'reconciled': True, 'amount_currency': -419.85},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((139.95, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm2.outstanding_account_id.id, 'partner_id': False, 'debit': 279.9, 'credit': 0, 'reconciled': False, 'amount_currency': 139.95},
                            {'account_id': self.bank_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 279.9, 'reconciled': True, 'amount_currency': -139.95},
                        ]
                    }),
                ],
            },
        })

    def test_03_orders_with_invoice(self):
        """ orders with invoice

        Orders
        ======
        +---------+----------+---------------+----------+-----+-------+
        | order   | payments | invoiced?     | product  | qty | total |
        +---------+----------+---------------+----------+-----+-------+
        | order 1 | cash     | no            | product1 |  10 |    50 |
        |         |          |               | product2 |  10 | 129.9 |
        |         |          |               | product3 |  10 |   150 |
        +---------+----------+---------------+----------+-----+-------+
        | order 2 | cash     | yes, customer | product1 |   5 |    25 |
        |         |          |               | product2 |   5 | 64.95 |
        +---------+----------+---------------+----------+-----+-------+
        | order 3 | bank     | yes, customer | product2 |   5 | 64.95 |
        |         |          |               | product3 |   5 |    75 |
        +---------+----------+---------------+----------+-----+-------+

        Expected Result
        ===============
        +---------------------+---------+-----------------+
        | account             | balance | amount_currency |
        +---------------------+---------+-----------------+
        | sale_account        |  -659.8 |         -329.90 |
        | pos receivable bank |   279.9 |          139.95 |
        | pos receivable cash |   839.7 |          419.85 |
        | invoice receivable  |  -179.9 |          -89.95 |
        | invoice receivable  |  -279.9 |         -139.95 |
        +---------------------+---------+-----------------+
        | Total balance       |     0.0 |            0.00 |
        +---------------------+---------+-----------------+
        """

        def _before_closing_cb():
            # check values before closing the session
            self.assertEqual(3, self.pos_session.order_count)
            orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
            self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        self._run_test({
            'payment_methods': self.cash_pm2 | self.bank_pm2,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 10), (self.product3, 10)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 5), (self.product2, 5)], 'is_invoiced': True, 'customer': self.customer, 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product2, 5), (self.product3, 5)], 'payments': [(self.bank_pm2, 139.95)], 'is_invoiced': True, 'customer': self.customer, 'uuid': '00100-010-0003'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {
                '00100-010-0002': {
                    'payments': [
                        ((self.cash_pm2, 89.95), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 179.90, 'reconciled': True, 'amount_currency': -89.95},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 179.90, 'credit': 0, 'reconciled': False, 'amount_currency': 89.95},
                            ]
                        }),
                    ],
                },
                '00100-010-0003': {
                    'payments': [
                        ((self.bank_pm2, 139.95), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 279.9, 'reconciled': True, 'amount_currency': -139.95},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 279.9, 'credit': 0, 'reconciled': False, 'amount_currency': 139.95},
                            ]
                        }),
                    ],
                },
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 659.8, 'reconciled': False, 'amount_currency': -329.90},
                        {'account_id': self.bank_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 279.9, 'credit': 0, 'reconciled': True, 'amount_currency': 139.95},
                        {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 839.7, 'credit': 0, 'reconciled': True, 'amount_currency': 419.85},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 179.90, 'reconciled': True, 'amount_currency': -89.95},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 279.9, 'reconciled': True, 'amount_currency': -139.95},
                    ],
                },
                'cash_statement': [
                    ((419.85, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm2.journal_id.default_account_id.id, 'partner_id': False, 'debit': 839.7, 'credit': 0, 'reconciled': False, 'amount_currency': 419.85},
                            {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 839.7, 'reconciled': True, 'amount_currency': -419.85},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((139.95, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm2.outstanding_account_id.id, 'partner_id': False, 'debit': 279.9, 'credit': 0, 'reconciled': False, 'amount_currency': 139.95},
                            {'account_id': self.bank_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 279.9, 'reconciled': True, 'amount_currency': -139.95},
                        ]
                    }),
                ],
            },
        })

    @skip('Temporary to fast merge new valuation')
    def test_04_anglo_saxon_products(self):
        """
        ======
        Orders
        ======
        +---------+----------+-----------+----------+-----+----------+------------+
        | order   | payments | invoiced? | product  | qty |    total | total cost |
        |         |          |           |          |     |          |            |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 1 | cash     | no        | product4 |   7 |      700 |        350 |
        |         |          |           | product5 |   7 |     1400 |        490 |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 2 | cash     | no        | product5 |   6 |     1200 |        420 |
        |         |          |           | product4 |   6 |      600 |        300 |
        |         |          |           | product6 |  49 |   2219.7 |     525.77 |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 3 | cash     | no        | product5 |   2 |      400 |        140 |
        |         |          |           | product6 |  13 |    588.9 |     139.49 |
        +---------+----------+-----------+----------+-----+----------+------------+
        | order 4 | cash     | no        | product6 |   1 |     45.3 |      10.73 |
        +---------+----------+-----------+----------+-----+----------+------------+

        ===============
        Expected Result
        ===============
        +---------------------+------------+-----------------+
        | account             |    balance | amount_currency |
        +---------------------+------------+-----------------+
        | sale_account        |   -7153.90 |        -3576.95 |
        | pos_receivable-cash |    7153.90 |         3576.95 |
        | expense_account     |    2375.99 |         2375.99 |
        | output_account      |   -2375.99 |        -2375.99 |
        +---------------------+------------+-----------------+
        | Total balance       |       0.00 |            0.00 |
        +---------------------+------------+-----------------+
        """

        self._run_test({
            'payment_methods': self.cash_pm2,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product4, 7), (self.product5, 7)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product5, 6), (self.product4, 6), (self.product6, 49)], 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product5, 2), (self.product6, 13)], 'uuid': '00100-010-0003'},
                {'pos_order_lines_ui_args': [(self.product6, 1)], 'uuid': '00100-010-0004'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 7153.90, 'reconciled': False, 'amount_currency': -3576.95},
                        {'account_id': self.expense_account.id, 'partner_id': False, 'debit': 2375.99, 'credit': 0, 'reconciled': False, 'amount_currency': 2375.99},
                        {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 7153.90, 'credit': 0, 'reconciled': True, 'amount_currency': 3576.95},
                        {'account_id': self.output_account.id, 'partner_id': False, 'debit': 0, 'credit': 2375.99, 'reconciled': True, 'amount_currency': -2375.99},
                    ],
                },
                'cash_statement': [
                    ((3576.95, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm2.journal_id.default_account_id.id, 'partner_id': False, 'debit': 7153.90, 'credit': 0, 'reconciled': False, 'amount_currency': 3576.95},
                            {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 7153.90, 'reconciled': True, 'amount_currency': -3576.95},
                        ]
                    }),
                ],
                'bank_payments': [],
            },
        })

    def test_05_tax_base_amount(self):
        self._run_test({
            'payment_methods': self.cash_pm2,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product7, 7)], 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 3.43, 'reconciled': False, 'amount_currency': -1.715, 'tax_base_amount': 49},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 49, 'reconciled': False, 'amount_currency': -24.5, 'tax_base_amount': 0},
                        {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 52.43, 'credit': 0, 'reconciled': True, 'amount_currency': 26.215, 'tax_base_amount': 0},
                    ],
                },
                'cash_statement': [
                    ((26.215, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm2.journal_id.default_account_id.id, 'partner_id': False, 'debit': 52.43, 'credit': 0, 'reconciled': False, 'amount_currency': 26.215},
                            {'account_id': self.cash_pm2.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 52.43, 'reconciled': True, 'amount_currency': -26.215},
                        ]
                    }),
                ],
                'bank_payments': [],
            },
        })

    def test_bank_journal_balance(self):
        """Verify that debit and credit are balanced when adding a difference to the bank."""

        # Make a sale paid by bank
        self.other_currency_config.open_ui()
        session_id = self.other_currency_config.current_session_id
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session_id.id,
            'partner_id': False,
            'lines': [(0, 0, {
                'name': 'OL/0001',
                'product_id': self.product1.id,
                'price_unit': 10.00,
                'discount': 0,
                'qty': 1,
                'tax_ids': False,
                'price_subtotal': 10.00,
                'price_subtotal_incl': 10.00,
            })],
            'pricelist_id': self.other_currency_config.pricelist_id.id,
            'amount_paid': 10.00,
            'amount_total': 10.00,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
        })

        # Make payment
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': self.bank_pm2.id
        })
        order_payment.with_context(**payment_context).check()

        # Close session with counted +10 for bank compared with expected
        session_id.action_pos_session_closing_control(bank_payment_method_diffs={self.bank_pm2.id: 10.00})  # Real 20, expected 10, diff 10

        # Check debit/credit session's balance
        for move in session_id._get_related_account_moves():
            debit = credit = 0.0
            for line in move.line_ids:
                debit += line.debit
                credit += line.credit
            self.assertEqual(tools.float_compare(debit, credit, precision_rounding=self.other_currency_config.currency_id.rounding), 0)  # debit and credit should be equal
