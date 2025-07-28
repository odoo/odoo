# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo import tools
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSMultipleReceivableAccounts(TestPoSCommon):
    """ Test for invoiced orders with customers having receivable account different from default

    Thus, for this test, there are two receivable accounts involved and are set in the
    customers.
        self.customer -> self.receivable_account
        self.other_customer -> self.other_receivable_account

    ADDITIONALLY, this tests different sales account on the products.

    NOTE That both receivable accounts above are different from the pos receivable account.
    """

    def setUp(self):
        super(TestPoSMultipleReceivableAccounts, self).setUp()
        self.config = self.basic_config
        self.product1 = self.create_product(
            'Product 1',
            self.categ_basic,
            lst_price=10.99,
            standard_price=5.0,
            tax_ids=self.taxes['tax7'].ids,
        )
        self.product2 = self.create_product(
            'Product 2',
            self.categ_basic,
            lst_price=19.99,
            standard_price=10.0,
            tax_ids=self.taxes['tax10'].ids,
            sale_account=self.other_sale_account,
        )
        self.product3 = self.create_product(
            'Product 3',
            self.categ_basic,
            lst_price=30.99,
            standard_price=15.0,
            tax_ids=self.taxes['tax_group_7_10'].ids,
        )
        self.adjust_inventory([self.product1, self.product2, self.product3], [100, 50, 50])

    def test_01_invoiced_order_from_other_customer(self):
        """
        Orders
        ======
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order   | payments | invoiced? | product  | qty | untaxed | tax                      | total  |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order 1 | cash     | no        | product1 | 10  | 109.9   | 7.69 [7%]                | 117.59 |
        |         |          |           | product2 | 10  | 181.73  | 18.17 [10%]              | 199.9  |
        |         |          |           | product3 | 10  | 281.73  | 19.72 [7%] + 28.17 [10%] | 329.62 |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order 2 | bank     | no        | product1 | 5   | 54.95   | 3.85 [7%]                | 58.80  |
        |         |          |           | product2 | 5   | 90.86   | 9.09 [10%]               | 99.95  |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+
        | order 3 | bank     | yes       | product2 | 5   | 90.86   | 9.09 [10%]               | 99.95  |
        |         |          |           | product3 | 5   | 140.86  | 9.86 [7%] + 14.09 [10%]  | 164.81 |
        +---------+----------+-----------+----------+-----+---------+--------------------------+--------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        | -164.85 |
        | sale_account        | -281.73 |
        | other_sale_account  | -272.59 |
        | tax 7%              |  -31.26 |
        | tax 10%             |  -55.43 |
        | pos receivable cash |  647.11 |
        | pos receivable bank |  423.51 |
        | other receivable    | -264.76 |
        +---------------------+---------+
        | Total balance       |    0.00 |
        +---------------------+---------+
        """

        def _before_closing_cb():
            # check values before closing the session
            self.assertEqual(3, self.pos_session.order_count)
            orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
            self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

            # check if there is one invoiced order
            self.assertEqual(len(self.pos_session.order_ids.filtered(lambda order: order.account_move)), 1, 'There should only be one invoiced order.')

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 10), (self.product3, 10)], 'uuid': '00100-010-0001'},
                {'pos_order_lines_ui_args': [(self.product1, 5), (self.product2, 5)], 'payments': [(self.bank_pm1, 158.75)], 'uuid': '00100-010-0002'},
                {'pos_order_lines_ui_args': [(self.product2, 5), (self.product3, 5)], 'payments': [(self.bank_pm1, 264.76)], 'is_invoiced': True, 'customer': self.other_customer, 'uuid': '09876-098-0987'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {
                '09876-098-0987': {
                    'invoice': {
                        'line_ids_predicate': lambda line: line.account_id in self.other_sale_account | self.sales_account | self.other_receivable_account,
                        'line_ids': [
                            {'account_id': self.other_sale_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 90.86, 'reconciled': False},
                            {'account_id': self.sales_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 140.87, 'reconciled': False},
                            {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 264.76, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 264.76), {
                            'line_ids': [
                                {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 264.76, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 264.76, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 31.26, 'reconciled': False},
                        {'account_id': self.tax_received_account.id, 'partner_id': False, 'debit': 0, 'credit': 55.44, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 164.85, 'reconciled': False},
                        {'account_id': self.other_sale_account.id, 'partner_id': False, 'debit': 0, 'credit': 272.59, 'reconciled': False},
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 281.72, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 423.51, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 647.11, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 264.76, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((647.11, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 647.11, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 647.11, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((423.51, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 423.51, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 423.51, 'reconciled': True},
                        ]
                    }),
                ],
            },
        })

    def test_02_all_orders_invoiced_mixed_customers(self):
        """
        Orders
        ======
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+
        | order   | payments | invoiced?           | product  | qty | untaxed | tax                      |  total |
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+
        | order 1 | cash     | yes, other_customer | product1 |  10 |  109.90 | 7.69 [7%]                | 117.59 |
        |         |          |                     | product2 |  10 |  181.73 | 18.17 [10%]              | 199.90 |
        |         |          |                     | product3 |  10 |  281.73 | 19.72 [7%] + 28.17 [10%] | 329.62 |
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+
        | order 2 | bank     | yes, customer       | product1 |   5 |   54.95 | 3.85 [7%]                |  58.80 |
        |         |          |                     | product2 |   5 |   90.86 | 9.09 [10%]               |  99.95 |
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+
        | order 3 | bank     | yes, other customer | product2 |   5 |   90.86 | 9.09 [10%]               |  99.95 |
        |         |          |                     | product3 |   5 |  140.86 | 9.86 [7%] + 14.09 [10%]  | 164.81 |
        +---------+----------+---------------------+----------+-----+---------+--------------------------+--------+

        Expected Result
        ===============
        +----------------------+---------+
        | account              | balance |
        +----------------------+---------+
        | pos receivable cash  |  647.11 |
        | pos receivable bank  |  423.51 |
        | received bank        | -423.51 |
        | received cash        | -647.11 |
        +----------------------+---------+
        | Total balance        |    0.00 |
        +----------------------+---------+

        """

        def _before_closing_cb():
            # check values before closing the session
            self.assertEqual(3, self.pos_session.order_count)
            orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
            self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

            # check if there is one invoiced order
            self.assertEqual(len(self.pos_session.order_ids.filtered(lambda order: order.account_move)), 3, 'All orders should be invoiced.')

        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product1, 10), (self.product2, 10), (self.product3, 10)], 'is_invoiced': True, 'customer': self.other_customer, 'uuid': '09876-098-0987'},
                {'pos_order_lines_ui_args': [(self.product1, 5), (self.product2, 5)], 'payments': [(self.bank_pm1, 158.75)], 'is_invoiced': True, 'customer': self.customer, 'uuid': '09876-098-0988'},
                {'pos_order_lines_ui_args': [(self.product2, 5), (self.product3, 5)], 'payments': [(self.bank_pm1, 264.76)], 'is_invoiced': True, 'customer': self.other_customer, 'uuid': '09876-098-0989'},
            ],
            'before_closing_cb': _before_closing_cb,
            'journal_entries_before_closing': {
                '09876-098-0987': {
                    'invoice': {
                        'line_ids_predicate': lambda line: line.account_id in self.other_sale_account | self.sales_account | self.other_receivable_account,
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 109.90, 'reconciled': False},
                            {'account_id': self.other_sale_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 181.73, 'reconciled': False},
                            {'account_id': self.sales_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 281.72, 'reconciled': False},
                            {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 647.11, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.cash_pm1, 647.11), {
                            'line_ids': [
                                {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 647.11, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 647.11, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
                '09876-098-0988': {
                    'invoice': {
                        'line_ids_predicate': lambda line: line.account_id in self.other_sale_account | self.sales_account | self.c1_receivable,
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 54.95, 'reconciled': False},
                            {'account_id': self.other_sale_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 90.86, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 158.75, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 158.75), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 158.75, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 158.75, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
                '09876-098-0989': {
                    'invoice': {
                        'line_ids_predicate': lambda line: line.account_id in self.other_sale_account | self.sales_account | self.other_receivable_account,
                        'line_ids': [
                            {'account_id': self.other_sale_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 90.86, 'reconciled': False},
                            {'account_id': self.sales_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 140.87, 'reconciled': False},
                            {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 264.76, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 264.76), {
                            'line_ids': [
                                {'account_id': self.other_receivable_account.id, 'partner_id': self.other_customer.id, 'debit': 0, 'credit': 264.76, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 264.76, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                },
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 423.51, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 647.11, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 647.11, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 423.51, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((647.11, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 647.11, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 647.11, 'reconciled': True},
                        ]
                    }),
                ],
                'bank_payments': [
                    ((423.51, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 423.51, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 423.51, 'reconciled': True},
                        ]
                    }),
                ],
            },
        })
