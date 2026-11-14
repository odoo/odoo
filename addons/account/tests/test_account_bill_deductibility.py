from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountBillPartialDeductibility(AccountTestInvoicingCommon):

    def test_simple_bill_partial_deductibility(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                })
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 25.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 3.75,   'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 11.25,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -115.0, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

        bill.invoice_line_ids[0].quantity = 2
        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 200.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -50.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 7.5,    'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 22.5,   'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -230.0, 'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 50.0,   'tax_ids': []},  # noqa: E241
            ],
            {}
        )

        bill.invoice_line_ids[0].price_unit = 50.0
        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 3.75,   'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 11.25,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -115.0, 'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 25.0,   'tax_ids': []},  # noqa: E241
            ],
            {}
        )

        bill.invoice_line_ids[0].deductible_amount = 100.0
        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',      'name': 'Partial item', 'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'tax',          'name': '15%',          'balance': 15.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term', 'name': False,          'balance': -115.0, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

        bill.invoice_line_ids[0].deductible_amount = 75.0
        bill.action_post()
        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',                        'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',                        'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                                 'balance': 11.25,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                                 'balance': -115.0, 'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': bill.name + ' - private part',         'balance': 25.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': bill.name + ' - private part (taxes)', 'balance': 3.75,   'tax_ids': []},  # noqa: E241
            ],
            {}
        )

        bill.button_draft()
        bill.invoice_line_ids[0].deductible_amount = 99.0
        bill.action_post()
        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',                        'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',                        'balance': -1.0,   'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                                 'balance': 14.85,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                                 'balance': -115.0, 'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': bill.name + ' - private part (taxes)', 'balance': 0.15,   'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': bill.name + ' - private part',         'balance': 1.0,    'tax_ids': []},  # noqa: E241
            ],
            {}
        )

    def test_bill_partial_deductibility_with_identical_lines(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                }),
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                })
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 50.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 7.5,    'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 22.5,   'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -230.0, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

    def test_bill_partial_deductibility_with_several_invoice_lines(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item 1',
                    'price_unit': 100,
                    'quantity': 3,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                }),
                Command.create({
                    'name': 'Partial item 2',
                    'price_unit': 150,
                    'quantity': 1,
                    'deductible_amount': 80.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                }),
                Command.create({
                    'name': 'Full item',
                    'price_unit': 200,
                    'quantity': 1,
                    'deductible_amount': 100.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                }),
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Full item',            'balance': 200.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'product',                      'name': 'Partial item 1',       'balance': 300.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'product',                      'name': 'Partial item 2',       'balance': 150.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item 1',       'balance': -75.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item 2',       'balance': -30.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 105.0,  'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 15.75,  'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 81.75,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -747.5, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

    def test_bill_partial_deductibility_with_different_taxes(self):
        tax_21 = self.tax_purchase_a.copy({
            'name': '21%',
            'amount': 21,
        })
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [
                        Command.set((self.tax_purchase_a + tax_21).ids),
                    ],
                })
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id, tax_21.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id, tax_21.id]},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 25.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 9.0,    'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 11.25,  'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '21%',                  'balance': 15.75,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -136.0, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

    def test_bill_partial_deductibility_with_several_lines_with_different_taxes(self):
        tax_21 = self.tax_purchase_a.copy({
            'name': '21%',
            'amount': 21,
        })
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item 1',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [
                        Command.set(self.tax_purchase_a.ids),
                    ],
                }),
                Command.create({
                    'name': 'Partial item 2',
                    'price_unit': 120,
                    'quantity': 2,
                    'deductible_amount': 50.00,
                    'tax_ids': [
                        Command.set(tax_21.ids),
                    ],
                })
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item 1',       'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'product',                      'name': 'Partial item 2',       'balance': 240.0,  'tax_ids': [tax_21.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item 1',       'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item 2',       'balance': -120.0, 'tax_ids': [tax_21.id]},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 145.0,  'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 28.95,  'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 11.25,  'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '21%',                  'balance': 25.2,   'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -405.4, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

    def test_bill_partial_deductibility_with_discounts(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'discount': 50,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                })
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 50.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -12.5, 'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 12.5,  'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 1.88,  'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 5.63,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -57.51, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

    def test_bill_partial_deductibility_with_cash_rounding(self):
        cash_rounding = self.env['account.cash.rounding'].create({
            'name': 'Rounding 10',
            'rounding_method': 'HALF-UP',
            'rounding': 10,
            'profit_account_id': self.cash_rounding_a.profit_account_id.id,
            'loss_account_id': self.cash_rounding_a.loss_account_id.id,
        })
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_cash_rounding_id': cash_rounding.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                })
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 25.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 3.75,   'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 11.25,  'tax_ids': []},  # noqa: E241
                {'display_type': 'rounding',                     'name': 'Rounding 10',          'balance' : 5.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -120.0, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

    def test_simple_refund_partial_deductibility(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_refund',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                })
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': -100.0, 'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': 25.0,   'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': -25.0,  'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': -3.75,  'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': -11.25, 'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': 115.0,  'tax_ids': []},  # noqa: E241
            ],
            {}
        )

    def test_bill_non_deductible_tax_in_tax_totals(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                })
            ]
        })

        expected_values = {
            'same_tax_base': False,
            'currency_id': self.env.company.currency_id.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': 15.0,
            'total_amount_currency': 115.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 15.0,
                    'tax_groups': [
                        {
                            'id': self.tax_purchase_a.tax_group_id.id,
                            'non_deductible_tax_amount': -3.75,
                            'non_deductible_tax_amount_currency': -3.75,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 15.0,
                            'display_base_amount_currency': 75.0,
                        },
                    ],
                },
            ],
        }
        self._assert_tax_totals_summary(bill.tax_totals, expected_values)

    def test_refund_non_deductible_tax_in_tax_totals(self):
        refund = self.env['account.move'].create({
            'move_type': 'in_refund',
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                })
            ]
        })

        expected_values = {
            'same_tax_base': False,
            'currency_id': self.env.company.currency_id.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': 15.0,
            'total_amount_currency': 115.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 15.0,
                    'tax_groups': [
                        {
                            'id': self.tax_purchase_a.tax_group_id.id,
                            'non_deductible_tax_amount': -3.75,
                            'non_deductible_tax_amount_currency': -3.75,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 15.0,
                            'display_base_amount_currency': 75.0,
                        },
                    ],
                },
            ],
        }
        self._assert_tax_totals_summary(refund.tax_totals, expected_values)

    def test_bill_partial_deductibility_with_reverse_charge(self):
        tax_reverse_charge = self.env['account.tax'].create({
            'name': 'Reverse Charge 20%',
            'amount_type': 'percent',
            'amount': 20.0,
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0, 'account_id': self.company_data['default_account_tax_purchase'].id}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0, 'account_id': self.company_data['default_account_tax_purchase'].id}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0, 'account_id': self.company_data['default_account_tax_purchase'].id}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0, 'account_id': self.company_data['default_account_tax_purchase'].id}),
            ],
        })

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                Command.create({
                    'name': 'RC Partial Item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 60.00,
                    'tax_ids': [Command.set(tax_reverse_charge.ids)],
                })
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'RC Partial Item',       'balance': 100.0,   'tax_ids': [tax_reverse_charge.id]},
                {'display_type': 'non_deductible_product',       'name': 'RC Partial Item',       'balance': -40.0,   'tax_ids': [tax_reverse_charge.id]},
                {'display_type': 'non_deductible_product_total', 'name': 'private part',          'balance': 40.0,    'tax_ids': []},
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)',  'balance': 8.0,     'tax_ids': []},
                {'display_type': 'tax',                          'name': 'Reverse Charge 20%',    'balance': -20.0,   'tax_ids': []},
                {'display_type': 'tax',                          'name': 'Reverse Charge 20%',    'balance': 12.0,    'tax_ids': []},
                {'display_type': 'payment_term',                 'name': False,                   'balance': -100.0,  'tax_ids': []},
            ],
            {}
        )

    def test_simple_receipt_partial_deductibility(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_receipt',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Partial item',
                    'price_unit': 100,
                    'quantity': 1,
                    'deductible_amount': 75.00,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                })
            ]
        })

        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 25.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 3.75,   'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 11.25,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -115.0, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

        bill.invoice_line_ids[0].quantity = 2
        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 200.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -50.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 7.5,    'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 22.5,   'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -230.0, 'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 50.0,   'tax_ids': []},  # noqa: E241
            ],
            {}
        )

        bill.invoice_line_ids[0].price_unit = 50.0
        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',         'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',         'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': 'private part (taxes)', 'balance': 3.75,   'tax_ids': []},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                  'balance': 11.25,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                  'balance': -115.0, 'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': 'private part',         'balance': 25.0,   'tax_ids': []},  # noqa: E241
            ],
            {}
        )

        bill.invoice_line_ids[0].deductible_amount = 100.0
        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',      'name': 'Partial item', 'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'tax',          'name': '15%',          'balance': 15.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term', 'name': False,          'balance': -115.0, 'tax_ids': []},  # noqa: E241
            ],
            {}
        )

        bill.invoice_line_ids[0].deductible_amount = 75.0
        bill.action_post()
        self.assertInvoiceValues(
            bill,
            [
                {'display_type': 'product',                      'name': 'Partial item',                        'balance': 100.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'non_deductible_product',       'name': 'Partial item',                        'balance': -25.0,  'tax_ids': [self.tax_purchase_a.id]},  # noqa: E241
                {'display_type': 'tax',                          'name': '15%',                                 'balance': 11.25,  'tax_ids': []},  # noqa: E241
                {'display_type': 'payment_term',                 'name': False,                                 'balance': -115.0, 'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_product_total', 'name': bill.name + ' - private part',         'balance': 25.0,   'tax_ids': []},  # noqa: E241
                {'display_type': 'non_deductible_tax',           'name': bill.name + ' - private part (taxes)', 'balance': 3.75,   'tax_ids': []},  # noqa: E241
            ],
            {}
        )


@tagged('post_install', '-at_install')
class TestAccountBillPartialDeductibilityCurrency(AccountTestInvoicingCommon):
    country_code = 'AU'
    chart_template = 'au'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_currency = cls.env.company.currency_id
        cls.third_currency = cls.setup_other_currency(
            'GBP', rates=[(fields.Date.today(), 0.40)],
        )
        cls.product = cls._create_product(name='Partial item', lst_price=100.0)

    def _make_private_base_purchase(
        self, *, rate=0.60, refund=False, included=False, company_currency=False, unsaved=False,
    ):
        self.assertEqual(self.env.company.currency_id.name, "AUD")
        tax = self.env["account.tax"].create({
            "name": "Fabricated partial deductibility control",
            "amount_type": "percent",
            "amount": 10.0,
            "type_tax_use": "purchase",
            "price_include_override": "tax_included" if included else "tax_excluded",
        })
        currency = self.company_currency if company_currency else self.third_currency
        line = self._prepare_invoice_line(
            product_id=self.product,
            price_unit=110.0 if included else 100.0,
            quantity=5,
            tax_ids=tax,
            deductible_amount=50,
        )
        values = {
            "move_type": "in_refund" if refund else "in_invoice",
            "invoice_date": fields.Date.today(),
            "currency_id": currency.id,
            "invoice_currency_rate": rate,
            "partner_id": self.partner_a.id,
            "invoice_line_ids": [line],
        }
        invoice = self.env["account.move"].new(values) if unsaved else self._create_invoice(**values)
        self.assertEqual(invoice.currency_id, currency)
        self.assertAlmostEqual(invoice.invoice_currency_rate, rate, places=6)
        self.assertAlmostEqual(invoice.invoice_line_ids.price_subtotal, 500.0, places=2)
        return invoice

    def _assert_private_base_amounts(self, invoice, expected_company, expected_document):
        private = invoice.line_ids.filtered(lambda line: line.display_type == "non_deductible_product")
        total = invoice.line_ids.filtered(lambda line: line.display_type == "non_deductible_product_total")
        self.assertEqual(len(private), 1)
        self.assertEqual(len(total), 1)
        self.assertAlmostEqual(private.balance, -invoice.direction_sign * expected_company, places=2)
        self.assertAlmostEqual(private.amount_currency, -invoice.direction_sign * expected_document, places=2)
        self.assertAlmostEqual(total.balance, invoice.direction_sign * expected_company, places=2)
        self.assertAlmostEqual(total.amount_currency, invoice.direction_sign * expected_document, places=2)
        self.assertEqual(private.currency_id, invoice.currency_id)
        self.assertEqual(total.currency_id, invoice.currency_id)
        self.assertAlmostEqual(sum(invoice.line_ids.mapped("balance")), 0.0, places=2)
        self.assertAlmostEqual(sum(invoice.line_ids.mapped("amount_currency")), 0.0, places=2)

    def test_private_base_foreign_currency_amounts(self):
        invoice = self._make_private_base_purchase()
        # Half of GBP 500 is GBP 250; at 0.60 GBP/AUD this is AUD 416.67.
        self._assert_private_base_amounts(invoice, 416.67, 250.0)

    def test_private_base_rate_only_refresh(self):
        invoice = self._make_private_base_purchase(rate=1.0)
        self._assert_private_base_amounts(invoice, 250.0, 250.0)
        invoice.write({"invoice_currency_rate": 0.50})
        self.assertAlmostEqual(invoice.invoice_currency_rate, 0.50, places=6)
        self._assert_private_base_amounts(invoice, 500.0, 250.0)

    def test_private_base_foreign_refund_sign(self):
        invoice = self._make_private_base_purchase(refund=True)
        self._assert_private_base_amounts(invoice, 416.67, 250.0)

    def test_private_base_price_included(self):
        invoice = self._make_private_base_purchase(included=True)
        self._assert_private_base_amounts(invoice, 416.67, 250.0)

    def test_private_base_company_currency_control(self):
        invoice = self._make_private_base_purchase(rate=1.0, company_currency=True)
        self._assert_private_base_amounts(invoice, 250.0, 250.0)

    def _assert_unsaved_private_taxes(self, invoice):
        self.assertFalse(invoice.id)
        bases, tax_lines = invoice._get_rounded_base_and_tax_lines(round_from_tax_lines=False)
        self.assertFalse(tax_lines)
        # The taxable business half is GBP 250, hence GBP 25 tax.
        tax_amount = sum(
            base["tax_details"]["total_included_currency"]
            - base["tax_details"]["total_excluded_currency"]
            for base in bases
        )
        self.assertAlmostEqual(tax_amount, 25.0, places=2)
        private = [base for base in bases if base["special_type"] == "non_deductible"]
        self.assertEqual(len(private), 1)
        self.assertAlmostEqual(private[0]["rate"], 0.60, places=6)
        self.assertAlmostEqual(private[0]["tax_details"]["total_excluded_currency"], -250.0, places=2)
        self.assertAlmostEqual(private[0]["tax_details"]["total_excluded"], -416.67, places=2)
        tax = private[0]["tax_details"]["taxes_data"]
        self.assertEqual(len(tax), 1)
        self.assertAlmostEqual(tax[0]["raw_tax_amount_currency"], -25.0, places=2)
        self.assertAlmostEqual(tax[0]["raw_tax_amount"], -41.67, places=2)
        offset = [base for base in bases if not base["tax_ids"]]
        self.assertEqual(len(offset), 1)
        self.assertAlmostEqual(offset[0]["rate"], 0.60, places=6)
        self.assertAlmostEqual(offset[0]["tax_details"]["total_excluded_currency"], 250.0, places=2)
        self.assertAlmostEqual(offset[0]["tax_details"]["total_excluded"], 416.67, places=2)

    def test_private_base_unsaved_tax_computation(self):
        self._assert_unsaved_private_taxes(self._make_private_base_purchase(unsaved=True))

    def test_private_base_unsaved_refund_tax_computation(self):
        self._assert_unsaved_private_taxes(self._make_private_base_purchase(unsaved=True, refund=True))

    def test_private_base_direction_change(self):
        invoice = self._make_private_base_purchase(rate=1.0)
        self._assert_private_base_amounts(invoice, 250.0, 250.0)
        invoice.write({"move_type": "in_refund", "invoice_currency_rate": 1.0})
        self.assertAlmostEqual(invoice.invoice_currency_rate, 1.0, places=6)
        self.assertEqual(invoice.move_type, "in_refund")
        self._assert_private_base_amounts(invoice, 250.0, 250.0)
