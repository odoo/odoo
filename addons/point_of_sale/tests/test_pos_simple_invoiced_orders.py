# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPosSimpleInvoicedOrders(TestPoSCommon):
    """
    Each test case only make a single **invoiced** order.
    Name of each test corresponds to a sheet in: https://docs.google.com/spreadsheets/d/1mt2jRSDU7OONPBFjwyTcnhRjITQI8rGMLLQA5K3fAjo/edit?usp=sharing
    """

    def setUp(self):
        super(TestPosSimpleInvoicedOrders, self).setUp()
        self.config = self.basic_config
        self.product100 = self.create_product('Product_100', self.categ_basic, 100, 50)

    def test_01b(self):
        self._run_test({
            'payment_methods': self.cash_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.cash_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
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

    def test_02b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.bank_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {
                '00100-010-0001': {
                    'invoice': {
                        'journal_id': self.config.invoice_journal_id.id,
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 100), {
                            'journal_id': self.config.journal_id.id,
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
                    'journal_id': self.config.journal_id.id,
                    'line_ids': [
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((100, ), {
                        'journal_id': self.bank_pm1.journal_id.id,
                        'line_ids': [
                            {'account_id': self.bank_pm1.outstanding_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_03b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.pay_later_pm,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.pay_later_pm, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {
                '00100-010-0001': {
                    'invoice': {
                        'journal_id': self.config.invoice_journal_id.id,
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                        ]
                    },
                    'payments': [],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': False,
                'cash_statement': [],
                'bank_payments': [],
            },
        })

    def test_04b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_split_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.bank_split_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {
                '00100-010-0001': {
                    'invoice': {
                        'journal_id': self.config.invoice_journal_id.id,
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        ]
                    },
                    'payments': [
                        ((self.bank_split_pm1, 100), {
                            'journal_id': self.config.journal_id.id,
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
                    'journal_id': self.config.journal_id.id,
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                    ],
                },
                'cash_statement': [],
                'bank_payments': [
                    ((100, ), {
                        'journal_id': self.bank_split_pm1.journal_id.id,
                        'line_ids': [
                            {'account_id': self.bank_split_pm1.outstanding_account_id.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False},
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                        ]
                    })
                ],
            },
        })

    def test_05b(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.cash_split_pm1, 100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                        ((self.cash_split_pm1, 100), {
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
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
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

    def test_10b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.pay_later_pm,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.cash_pm1, 200), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                        ((self.cash_pm1, 200), {
                            'line_ids': [
                                # needs to check the residual because it's supposed to be partial reconciled
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': False, 'amount_residual': -100},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False, 'amount_residual': 200},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
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

    def test_11b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1 | self.pay_later_pm,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.bank_pm1, 200), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                        ((self.bank_pm1, 200), {
                            'line_ids': [
                                # needs to check the residual because it's supposed to be partial reconciled
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': False, 'amount_residual': -100},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False, 'amount_residual': 200},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
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

    def test_12b(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1 | self.pay_later_pm,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.cash_split_pm1, 200), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                        ((self.cash_split_pm1, 200), {
                            'line_ids': [
                                # needs to check the residual because it's supposed to be partial reconciled
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': False, 'amount_residual': -100},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False, 'amount_residual': 200},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
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

    def test_13b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_split_pm1 | self.pay_later_pm,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.bank_split_pm1, 200), (self.pay_later_pm, -100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                        ((self.bank_split_pm1, 200), {
                            'line_ids': [
                                # needs to check the residual because it's supposed to be partial reconciled
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': False, 'amount_residual': -100},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False, 'amount_residual': 200},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
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

    def test_14b(self):
        self._run_test({
            'payment_methods': self.cash_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.cash_pm1, 200), (self.cash_pm1, -100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                        ((self.cash_pm1, 200), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                        ((self.cash_pm1, -100), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
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

    def test_15b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.bank_pm1, 200), (self.cash_pm1, -100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                        ((self.bank_pm1, 200), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                        ((self.cash_pm1, -100), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
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

    def test_16b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_split_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.bank_split_pm1, 200), (self.cash_pm1, -100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                        ((self.bank_split_pm1, 200), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                        ((self.cash_pm1, -100), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
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

    def test_17b(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.cash_split_pm1, 200), (self.cash_split_pm1, -100)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
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
                        ((self.cash_split_pm1, 200), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 200, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 200, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                        ((self.cash_split_pm1, -100), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 100, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 200, 'credit': 0, 'reconciled': True},
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 200, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 100, 'credit': 0, 'reconciled': True},
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

    def test_18b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.pay_later_pm,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.cash_pm1, 50), (self.pay_later_pm, 50)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {
                '00100-010-0001': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False, 'amount_residual': 0},
                            # needs to check the residual because it's supposed to be partial reconciled
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False, 'amount_residual': 50},
                        ]
                    },
                    'payments': [
                        ((self.cash_pm1, 50), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 50, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.cash_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 50, 'reconciled': True},
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

    def test_19b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_pm1 | self.pay_later_pm,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.bank_pm1, 50), (self.pay_later_pm, 50)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {
                '00100-010-0001': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False, 'amount_residual': 0},
                            # needs to check the residual because it's supposed to be partial reconciled
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False, 'amount_residual': 50},
                        ]
                    },
                    'payments': [
                        ((self.bank_pm1, 50), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 50, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.bank_pm1.receivable_account_id.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 50, 'reconciled': True},
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

    def test_20b(self):
        self._run_test({
            'payment_methods': self.cash_pm1 | self.bank_split_pm1 | self.pay_later_pm,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.bank_split_pm1, 50), (self.pay_later_pm, 50)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {
                '00100-010-0001': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False, 'amount_residual': 0},
                            # needs to check the residual because it's supposed to be partial reconciled
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False, 'amount_residual': 50},
                        ]
                    },
                    'payments': [
                        ((self.bank_split_pm1, 50), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 50, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 50, 'reconciled': True},
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

    def test_21b(self):
        self._run_test({
            'payment_methods': self.cash_split_pm1 | self.pay_later_pm,
            'orders': [
                {'pos_order_lines_ui_args': [(self.product100, 1)], 'payments': [(self.cash_split_pm1, 50), (self.pay_later_pm, 50)], 'customer': self.customer, 'is_invoiced': True, 'uuid': '00100-010-0001'},
            ],
            'journal_entries_before_closing': {
                '00100-010-0001': {
                    'invoice': {
                        'line_ids': [
                            {'account_id': self.sales_account.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 100, 'reconciled': False, 'amount_residual': 0},
                            # needs to check the residual because it's supposed to be partial reconciled
                            {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 100, 'credit': 0, 'reconciled': False, 'amount_residual': 50},
                        ]
                    },
                    'payments': [
                        ((self.cash_split_pm1, 50), {
                            'line_ids': [
                                {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 0, 'credit': 50, 'reconciled': True},
                                {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 50, 'credit': 0, 'reconciled': False},
                            ]
                        }),
                    ],
                }
            },
            'journal_entries_after_closing': {
                'session_journal_entry': {
                    'line_ids': [
                        {'account_id': self.c1_receivable.id, 'partner_id': self.customer.id, 'debit': 50, 'credit': 0, 'reconciled': True},
                        {'account_id': self.pos_receivable_account.id, 'partner_id': False, 'debit': 0, 'credit': 50, 'reconciled': True},
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
