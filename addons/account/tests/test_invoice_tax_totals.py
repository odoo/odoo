# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.fields import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxTotals(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.tax_group1 = cls.env['account.tax.group'].create({
            'name': '1',
            'sequence': 1
        })
        cls.tax_group2 = cls.env['account.tax.group'].create({
            'name': '2',
            'sequence': 2
        })
        cls.tax_group_sub1 = cls.env['account.tax.group'].create({
            'name': 'subtotals 1',
            'preceding_subtotal': "PRE GROUP 1",
            'sequence': 3
        })
        cls.tax_group_sub2 = cls.env['account.tax.group'].create({
            'name': 'subtotals 2',
            'preceding_subtotal': "PRE GROUP 2",
            'sequence': 4
        })
        cls.tax_group_sub3 = cls.env['account.tax.group'].create({
            'name': 'subtotals 3',
            'preceding_subtotal': "PRE GROUP 1", # same as sub1, on purpose
            'sequence': 5
        })

        cls.tax_10 = cls.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
        })
        cls.tax_16 = cls.env['account.tax'].create({
            'name': "tax_16",
            'amount_type': 'percent',
            'amount': 16.0,
        })
        cls.tax_53 = cls.env['account.tax'].create({
            'name': "tax_53",
            'amount_type': 'percent',
            'amount': 53.0,
        })
        cls.tax_17a = cls.env['account.tax'].create({
            'name': "tax_17a",
            'amount_type': 'percent',
            'amount': 17.0,
        })
        cls.tax_17b = cls.tax_17a.copy({'name': "tax_17b"})

    def assertTaxTotals(self, document, expected_values):
        main_keys_to_ignore = {'formatted_amount_total', 'formatted_amount_untaxed'}
        group_keys_to_ignore = {'group_key', 'formatted_tax_group_amount', 'formatted_tax_group_base_amount'}
        subtotals_keys_to_ignore = {'formatted_amount'}

        to_compare = document.tax_totals

        for key in main_keys_to_ignore:
            del to_compare[key]

        for key in group_keys_to_ignore:
            for groups in to_compare['groups_by_subtotal'].values():
                for group in groups:
                    del group[key]

        for key in subtotals_keys_to_ignore:
            for subtotal in to_compare['subtotals']:
                del subtotal[key]

        self.assertEqual(to_compare, expected_values)

    def _create_document_for_tax_totals_test(self, lines_data):
        """ Creates and returns a new record of a model defining a tax_totals
        field and using the related widget.

        By default, this function creates an invoice, but it is overridden in sale
        and purchase to create respectively a sale.order or a purchase.order. This way,
        we can test the invoice_tax_totals from both these models in the same way as
        account.move's.

        :param lines_data: a list of tuple (amount, taxes), where amount is a base amount,
                           and taxes a recordset of account.tax objects corresponding
                           to the taxes to apply on this amount. Each element of the list
                           corresponds to a line of the document (invoice line, PO line, SO line).
        """
        invoice_lines_vals = [
            (0, 0, {
                'name': 'line',
                'display_type': 'product',
                'account_id': self.company_data['default_account_revenue'].id,
                'price_unit': amount,
                'tax_ids': [(6, 0, taxes.ids)],
            })
        for amount, taxes in lines_data]

        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': invoice_lines_vals,
        })

    def test_multiple_tax_lines(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'tax_group_id': self.tax_group1.id,
        })

        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'tax_group_id': self.tax_group2.id,
        })

        document = self._create_document_for_tax_totals_test([
            (1000, tax_10 + tax_20),
            (1000, tax_10),
            (1000, tax_20),
        ])

        self.assertTaxTotals(document, {
            'amount_total': 3600,
            'amount_untaxed': 3000,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_amount': 200,
                        'tax_group_base_amount': 2000,
                        'tax_group_id': self.tax_group1.id,
                    },

                    {
                        'tax_group_name': self.tax_group2.name,
                        'tax_group_amount': 400,
                        'tax_group_base_amount': 2000,
                        'tax_group_id': self.tax_group2.id,
                    },
                ],
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 3000,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

        # Same but both are sharing the same tax group.

        tax_20.tax_group_id = self.tax_group1
        document.invalidate_model(['tax_totals'])

        self.assertTaxTotals(document, {
            'amount_total': 3600,
            'amount_untaxed': 3000,
            'display_tax_base': False,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_amount': 600,
                        'tax_group_base_amount': 3000,
                        'tax_group_id': self.tax_group1.id,
                    },
                ],
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 3000,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

    def test_zero_tax_lines(self):
        tax_0 = self.env['account.tax'].create({
            'name': "tax_0",
            'amount_type': 'percent',
            'amount': 0.0,
        })

        document = self._create_document_for_tax_totals_test([
            (1000, tax_0),
        ])

        self.assertTaxTotals(document, {
            'amount_total': 1000,
            'amount_untaxed': 1000,
            'display_tax_base': False,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': tax_0.tax_group_id.name,
                        'tax_group_amount': 0,
                        'tax_group_base_amount': 1000,
                        'tax_group_id': tax_0.tax_group_id.id,
                    },
                ],
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 1000,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

    def test_tax_affect_base_1(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'tax_group_id': self.tax_group1.id,
            'price_include': True,
            'include_base_amount': True,
        })

        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'tax_group_id': self.tax_group2.id,
        })

        document = self._create_document_for_tax_totals_test([
            (1100, tax_10 + tax_20),
            (1100, tax_10),
            (1000, tax_20),
        ])

        self.assertTaxTotals(document, {
            'amount_total': 3620,
            'amount_untaxed': 3000,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_amount': 200,
                        'tax_group_base_amount': 2000,
                        'tax_group_id': self.tax_group1.id,
                    },

                    {
                        'tax_group_name': self.tax_group2.name,
                        'tax_group_amount': 420,
                        'tax_group_base_amount': 2100,
                        'tax_group_id': self.tax_group2.id,
                    },
                ],
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 3000,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

        # Same but both are sharing the same tax group.

        tax_20.tax_group_id = self.tax_group1
        document.invalidate_model(['tax_totals'])

        self.assertTaxTotals(document, {
            'amount_total': 3620,
            'amount_untaxed': 3000,
            'display_tax_base': False,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_amount': 620,
                        'tax_group_base_amount': 3000,
                        'tax_group_id': self.tax_group1.id,
                    },
                ],
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 3000,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

    def test_tax_affect_base_2(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'tax_group_id': self.tax_group1.id,
            'include_base_amount': True,
            'sequence': 2,
        })

        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'tax_group_id': self.tax_group1.id,
            'sequence': 2,
        })

        tax_30 = self.env['account.tax'].create({
            'name': "tax_30",
            'amount_type': 'percent',
            'amount': 30.0,
            'tax_group_id': self.tax_group2.id,
            'include_base_amount': True,
            'sequence': 1,
        })

        document = self._create_document_for_tax_totals_test([
            (1000, tax_10 + tax_20),
            (1000, tax_30 + tax_10),
        ])

        self.assertTaxTotals(document, {
            'amount_total': 2750,
            'amount_untaxed': 2000,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_amount': 450,
                        'tax_group_base_amount': 2300,
                        'tax_group_id': self.tax_group1.id,
                    },

                    {
                        'tax_group_name': self.tax_group2.name,
                        'tax_group_amount': 300,
                        'tax_group_base_amount': 1000,
                        'tax_group_id': self.tax_group2.id,
                    },
                ],
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 2000,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

        # Same but both are sharing the same tax group.

        tax_30.tax_group_id = self.tax_group1
        document.invalidate_model(['tax_totals'])

        self.assertTaxTotals(document, {
            'amount_total': 2750,
            'amount_untaxed': 2000,
            'display_tax_base': False,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_amount': 750,
                        'tax_group_base_amount': 2000,
                        'tax_group_id': self.tax_group1.id,
                    },
                ],
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 2000,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

    def test_subtotals_basic(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'tax_group_id': self.tax_group_sub1.id,
        })

        tax_25 = self.env['account.tax'].create({
            'name': "tax_25",
            'amount_type': 'percent',
            'amount': 25.0,
            'tax_group_id': self.tax_group_sub2.id,
        })

        tax_42 = self.env['account.tax'].create({
            'name': "tax_42",
            'amount_type': 'percent',
            'amount': 42.0,
            'tax_group_id': self.tax_group1.id,
        })

        document = self._create_document_for_tax_totals_test([
            (1000, tax_10),
            (1000, tax_25),
            (100, tax_42),
            (200, tax_42 + tax_10 + tax_25),
        ])

        self.assertTaxTotals(document, {
            'amount_total': 2846,
            'amount_untaxed': 2300,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_amount': 126,
                        'tax_group_base_amount': 300,
                        'tax_group_id': self.tax_group1.id,
                    },
                ],
                'PRE GROUP 1': [
                    {
                        'tax_group_name': self.tax_group_sub1.name,
                        'tax_group_amount': 120,
                        'tax_group_base_amount': 1200,
                        'tax_group_id': self.tax_group_sub1.id,
                    },
                ],
                'PRE GROUP 2': [
                    {
                        'tax_group_name': self.tax_group_sub2.name,
                        'tax_group_amount': 300,
                        'tax_group_base_amount': 1200,
                        'tax_group_id': self.tax_group_sub2.id,
                    },
                ]
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 2300,
                },

                {
                    'name': "PRE GROUP 1",
                    'amount': 2426,
                },

                {
                    'name': "PRE GROUP 2",
                    'amount': 2546,
                },
            ],
            'subtotals_order': ["Untaxed Amount", "PRE GROUP 1", "PRE GROUP 2"],
        })

    def test_after_total_mix(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'tax_group_id': self.tax_group_sub3.id,
        })

        tax_25 = self.env['account.tax'].create({
            'name': "tax_25",
            'amount_type': 'percent',
            'amount': -25.0,
            'tax_group_id': self.tax_group_sub2.id,
        })

        tax_42 = self.env['account.tax'].create({
            'name': "tax_42",
            'amount_type': 'percent',
            'amount': 42.0,
            'tax_group_id': self.tax_group_sub1.id,
        })

        tax_30 = self.env['account.tax'].create({
            'name': "tax_30",
            'amount_type': 'percent',
            'amount': 30.0,
            'tax_group_id': self.tax_group1.id,
        })

        document = self._create_document_for_tax_totals_test([
            (100, tax_10),
            (100, tax_25 + tax_42 + tax_30),
            (200, tax_10 + tax_25),
            (1000, tax_30),
            (100, tax_30 + tax_10)
        ])

        self.assertTaxTotals(document, {
            'amount_total': 1867,
            'amount_untaxed': 1500,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_amount': 360,
                        'tax_group_base_amount': 1200,
                        'tax_group_id': self.tax_group1.id,
                    },
                ],

                'PRE GROUP 1': [
                    {
                        'tax_group_name': self.tax_group_sub1.name,
                        'tax_group_amount': 42,
                        'tax_group_base_amount': 100,
                        'tax_group_id': self.tax_group_sub1.id,
                    },

                    {
                        'tax_group_name': self.tax_group_sub3.name,
                        'tax_group_amount': 40,
                        'tax_group_base_amount': 400,
                        'tax_group_id': self.tax_group_sub3.id,
                    },
                ],

                'PRE GROUP 2': [
                    {
                        'tax_group_name': self.tax_group_sub2.name,
                        'tax_group_amount': -75,
                        'tax_group_base_amount': 300,
                        'tax_group_id': self.tax_group_sub2.id,
                    },
                ],
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 1500,
                },

                {
                    'name': "PRE GROUP 1",
                    'amount': 1860,
                },

                {
                    'name': "PRE GROUP 2",
                    'amount': 1942,
                },
            ],
            'subtotals_order': ["Untaxed Amount", "PRE GROUP 1", "PRE GROUP 2"],
        })

    def test_discounted_tax(self):
        tax_21_exempted = self.env['account.tax'].create({
            'name': "tax_21_exempted",
            'amount_type': 'group',
            'amount': 2.0,
            'tax_group_id': self.tax_group1.id,
            'children_tax_ids': [
                Command.create({
                    'name': "tax_exempt",
                    'amount_type': 'percent',
                    'amount': -2.0,
                    'include_base_amount': True,
                    'tax_group_id': self.tax_group_sub1.id,
                    'sequence': 1,
                }),
                Command.create({
                    'name': "tax_21",
                    'amount_type': 'percent',
                    'amount': 21.0,
                    'tax_group_id': self.tax_group_sub2.id,
                    'sequence': 2,
                }),
                Command.create({
                    'name': "tax_reapply",
                    'amount_type': 'percent',
                    'amount': 2.0,
                    'is_base_affected': False,
                    'tax_group_id': self.tax_group_sub3.id,
                    'sequence': 3,
                }),
            ]
        })
        self.tax_group_sub1.preceding_subtotal = "Tax exemption"
        self.tax_group_sub2.preceding_subtotal = "Tax application"
        self.tax_group_sub3.preceding_subtotal = "Reapply amount"

        document = self._create_document_for_tax_totals_test([
            (1000 / 0.98, tax_21_exempted),
        ])

        self.assertTaxTotals(document, {
            'amount_total': 1230.41,
            'amount_untaxed': 1020.41,
            'display_tax_base': True,
            'groups_by_subtotal': {
                "Reapply amount": [{
                    'tax_group_name': self.tax_group_sub3.name,
                    'tax_group_amount': 20.41,
                    'tax_group_base_amount': 1020.41,
                    'tax_group_id': self.tax_group_sub3.id,
                }],
                "Tax application": [{
                    'tax_group_name': self.tax_group_sub2.name,
                    'tax_group_amount': 210.0,
                    'tax_group_base_amount': 1000.0,
                    'tax_group_id': self.tax_group_sub2.id,
                }],
                "Tax exemption": [{
                    'tax_group_name': self.tax_group_sub1.name,
                    'tax_group_amount': -20.41,
                    'tax_group_base_amount': 1020.41,
                    'tax_group_id': self.tax_group_sub1.id,
                }],
            },
            'subtotals': [{
                'name': "Tax exemption",
                'amount': 1020.41,
            }, {
                'name': "Tax application",
                'amount': 1000.00,
            }, {
                'name': "Reapply amount",
                'amount': 1210.00,
            }],
            'subtotals_order': ["Tax exemption", "Tax application", "Reapply amount"],
        })

    def test_invoice_grouped_taxes_with_tax_group(self):
        """ A tax of type group with a tax_group_id being the same as one of the children tax shouldn't affect the
        result of the _prepare_tax_totals.
        """
        tax_10_withheld = self.env['account.tax'].create({
            'name': "tax_10_withheld",
            'amount_type': 'group',
            'tax_group_id': self.tax_group1.id,
            'children_tax_ids': [
                Command.create({
                    'name': "tax_withheld",
                    'amount_type': 'percent',
                    'amount': -47,
                    'tax_group_id': self.tax_group_sub1.id,
                    'sequence': 1,
                }),
                Command.create({
                    'name': "tax_10",
                    'amount_type': 'percent',
                    'amount': 10,
                    'tax_group_id': self.tax_group1.id,
                    'sequence': 2,
                }),
            ]
        })
        self.tax_group_sub1.preceding_subtotal = "Tax withholding"

        document = self._create_document_for_tax_totals_test([
            (100, tax_10_withheld),
        ])

        self.assertTaxTotals(document, {
            'amount_total': 63,
            'amount_untaxed': 100,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [{
                    'tax_group_name': self.tax_group1.name,
                    'tax_group_amount': 10,
                    'tax_group_base_amount': 100,
                    'tax_group_id': self.tax_group1.id,
                }],
                "Tax withholding": [{
                    'tax_group_name': self.tax_group_sub1.name,
                    'tax_group_amount': -47,
                    'tax_group_base_amount': 100,
                    'tax_group_id': self.tax_group_sub1.id,
                }],
            },
            'subtotals': [{
                'name': "Untaxed Amount",
                'amount': 100,
            }, {
                'name': "Tax withholding",
                'amount': 110,
            }],
            'subtotals_order': ["Untaxed Amount", "Tax withholding"],
        })

    def test_taxtotals_with_different_tax_rounding_methods(self):

        def run_case(rounding_line, lines, expected_tax_group_amounts):
            self.env.company.tax_calculation_rounding_method = rounding_line

            document = self._create_document_for_tax_totals_test(lines)
            tax_amounts = document.tax_totals['groups_by_subtotal']['Untaxed Amount']

            if len(expected_tax_group_amounts) != len(tax_amounts):
                self.fail("Wrong number of values to compare.")

            for tax_amount, expected in zip(tax_amounts, expected_tax_group_amounts):
                actual = tax_amount['tax_group_amount']
                if document.currency_id.compare_amounts(actual, expected) != 0:
                    self.fail(f'{document.currency_id.round(actual)} != {expected}')

        # one line, two taxes
        lines = [
            (100.41, self.tax_16 + self.tax_53),
        ]
        run_case('round_per_line', lines, [69.29])
        run_case('round_globally', lines, [69.29])

        # two lines, different taxes
        lines = [
            (50.4, self.tax_17a),
            (47.21, self.tax_17b),
        ]
        run_case('round_per_line', lines, [16.60])
        run_case('round_globally', lines, [16.60])

        # two lines, same tax
        lines = [
            (50.4, self.tax_17a),
            (47.21, self.tax_17a),
        ]
        run_case('round_per_line', lines, [16.60])
        run_case('round_globally', lines, [16.59])

        lines = [
            (54.45, self.tax_10),
            (600, self.tax_10),
            (-500, self.tax_10),
        ]
        run_case('round_per_line', lines, [15.45])
        run_case('round_globally', lines, [15.45])

    def test_cash_rounding_amount_total_rounded(self):
        tax_15 = self.env['account.tax'].create({
            'name': "tax_15",
            'amount_type': 'percent',
            'tax_group_id': self.tax_group1.id,
            'amount': 15.0,
        })
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'tax_group_id': self.tax_group2.id,
            'amount': 10.0,
        })
        cash_rounding_biggest_tax = self.env['account.cash.rounding'].create({
            'name': 'biggest tax Rounding HALF-UP',
            'rounding': 1,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
        })
        cash_rounding_add_invoice_line = self.env['account.cash.rounding'].create({
            'name': 'add invoice line Rounding HALF-UP',
            'rounding': 1,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
            'rounding_method': 'HALF-UP',
        })

        for move_type in ['out_invoice', 'in_invoice']:
            move = self.env['account.move'].create({
                'move_type': move_type,
                'partner_id': self.partner_a.id,
                'invoice_date': '2019-01-01',
                'invoice_line_ids': [
                        Command.create({
                            'name': 'line',
                            'display_type': 'product',
                            'price_unit': 378,
                            'tax_ids': [Command.set(tax_15.ids)],
                        }),
                        Command.create({
                            'name': 'line',
                            'display_type': 'product',
                            'price_unit': 100,
                            'tax_ids': [Command.set(tax_10.ids)],
                        })
                    ],
            })

            move.invoice_cash_rounding_id = cash_rounding_biggest_tax
            self.assertEqual(move.tax_totals['groups_by_subtotal']['Untaxed Amount'][0]['tax_group_amount'], 57)
            self.assertEqual(move.tax_totals['groups_by_subtotal']['Untaxed Amount'][1]['tax_group_amount'], 10)
            self.assertEqual(move.tax_totals['amount_total'], 545)

            move.invoice_cash_rounding_id = cash_rounding_add_invoice_line
            self.assertEqual(move.tax_totals['groups_by_subtotal']['Untaxed Amount'][0]['tax_group_amount'], 56.7)
            self.assertEqual(move.tax_totals['groups_by_subtotal']['Untaxed Amount'][1]['tax_group_amount'], 10)
            self.assertEqual(move.tax_totals['rounding_amount'], 0.3)
            self.assertEqual(move.tax_totals['amount_total'], 544.7)
            self.assertEqual(move.tax_totals['amount_total_rounded'], 545)

    def test_recompute_cash_rounding_lines(self):
        # if rounding_method is changed then rounding shouldn't be recomputed in posted invoices
        cash_rounding_add_invoice_line = self.env['account.cash.rounding'].create({
            'name': 'Add invoice line Rounding UP',
            'rounding': 1,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
            'rounding_method': 'UP',
        })
        moves_rounding = {}
        moves = self.env['account.move']
        for move_type in ['out_invoice', 'in_invoice']:
            move = self.env['account.move'].create({
                'move_type': move_type,
                'partner_id': self.partner_a.id,
                'invoice_date': '2019-01-01',
                'invoice_cash_rounding_id': cash_rounding_add_invoice_line.id,
                'invoice_line_ids': [
                        Command.create({
                            'name': 'line',
                            'display_type': 'product',
                            'price_unit': 99.5,
                        })
                    ],
            })
            moves_rounding[move] = sum(move.line_ids.filtered(lambda line: line.display_type == 'rounding').mapped('balance'))
            moves += move
        moves.action_post()
        cash_rounding_add_invoice_line.rounding_method = 'DOWN'
        # check if rounding is recomputed
        moves.to_check = True
        for move in moves_rounding:
            self.assertEqual(sum(move.line_ids.filtered(lambda line: line.display_type == 'rounding').mapped('balance')), moves_rounding[move])

    def test_cash_rounding_amount_total_rounded_foreign_currency(self):
        tax_15 = self.env['account.tax'].create({
            'name': "tax_15",
            'amount_type': 'percent',
            'amount': 15.0,
        })
        cash_rounding = self.env['account.cash.rounding'].create({
            'name': 'Rounding HALF-UP',
            'rounding': 10,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
        })
        self.env['res.currency.rate'].create({
            'name': '2023-01-01',
            'rate': 0.2,
            'currency_id': self.currency_data['currency'].id,
            'company_id': self.env.company.id,
        })
        for move_type in ['out_invoice', 'in_invoice']:
            move = self.env['account.move'].create({
                'move_type': move_type,
                'partner_id': self.partner_a.id,
                'invoice_date': '2023-01-01',
                'currency_id': self.currency_data['currency'].id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'line',
                        'display_type': 'product',
                        'price_unit': 100,
                        'tax_ids': [tax_15.id],
                    })
                ]
            })
            move.invoice_cash_rounding_id = cash_rounding
            self.assertEqual(move.tax_totals['amount_total'], 120)
