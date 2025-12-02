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
