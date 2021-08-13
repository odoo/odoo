# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPosSimpleOrders(TestPoSCommon):
    """
    Each test case only make a single order.
    Name of each test corresponds to a sheet in: https://docs.google.com/spreadsheets/d/1mt2jRSDU7OONPBFjwyTcnhRjITQI8rGMLLQA5K3fAjo/edit?usp=sharing
    """

    def setUp(self):
        super(TestPosSimpleOrders, self).setUp()
        self.config = self.basic_config
        self.product100 = self.create_product('Product_100', self.categ_basic, 100, 50)

    def test_01(self):
        self._run_test({
            'payment_methods': self.cash_pm1,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.cash_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })

    def test_02(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_03(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.pay_later_pm, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [],
            },
        })

    def test_04(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_split_pm1,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.bank_split_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.bank_split_pm1.outstanding_account_id.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_05(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.cash_split_pm1, 100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })

    def test_06(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [], 'payments': [(self.cash_pm1, 100), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })

    def test_07(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [], 'payments': [(self.bank_pm1, 100), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_08(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_split_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [], 'payments': [(self.bank_split_pm1, 100), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.bank_split_pm1.outstanding_account_id.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_09(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [], 'payments': [(self.cash_split_pm1, 100), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })

    def test_10(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.cash_pm1, 200), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((200, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })

    def test_11(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.bank_pm1, 200), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((200, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_12(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.cash_split_pm1, 200), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((200, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })

    def test_13(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_split_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.bank_split_pm1, 200), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((200, ), {
                        'line_ids': [
                            {'account_id': self.bank_split_pm1.outstanding_account_id.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_14(self):
        self._run_test({
            'payment_methods': self.cash_pm1,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.cash_pm1, 200), (self.cash_pm1, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((100, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })

    def test_15(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.bank_pm1, 200), (self.cash_pm1, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((-100, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [
                    ((200, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_16(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_split_pm1,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.bank_split_pm1, 200), (self.cash_pm1, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((-100, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [
                    ((200, ), {
                        'line_ids': [
                            {'account_id': self.bank_split_pm1.outstanding_account_id.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_17(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.cash_split_pm1, 200), (self.cash_split_pm1, -100)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((200, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': True},
                        ]
                    }),
                    ((-100, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })

    def test_18(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.cash_pm1, 50), (self.pay_later_pm, 50)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': False},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((50, ), {
                        'line_ids': [
                            {'account_id': self.cash_pm1.journal_id.default_account_id.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': False},
                            {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 50, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })

    def test_19(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.bank_pm1, 50), (self.pay_later_pm, 50)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((50, ), {
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 50, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_20(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_split_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.bank_split_pm1, 50), (self.pay_later_pm, 50)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': False},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((50, ), {
                        'line_ids': [
                            {'account_id': self.bank_split_pm1.outstanding_account_id.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 50, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_21(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1 | self.pay_later_pm,
            'orders': [
                {'product_quantity_pairs': [(self.product100, 1)], 'payments': [(self.cash_split_pm1, 50), (self.pay_later_pm, 50)], 'customer': self.customer, 'is_invoiced': False, 'uid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {},
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.sales_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': False},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': True},
                    ],
                },
                'cash_statement': [
                    ((50, ), {
                        'line_ids': [
                            {'account_id': self.cash_split_pm1.journal_id.default_account_id.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 50, 'reconciled': True},
                        ]
                    })
                ],
                'bank_payments': [],
            },
        })
