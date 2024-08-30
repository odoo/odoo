from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.fields import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxTotals(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.maxDiff = None

        cls.tax_group1 = cls.env['account.tax.group'].create({
            'name': '1',
            'sequence': 1,
            'pos_receipt_label': 'A',
        })
        cls.tax_group2 = cls.env['account.tax.group'].create({
            'name': '2',
            'sequence': 2,
            'pos_receipt_label': 'B',
        })
        cls.tax_group_sub1 = cls.env['account.tax.group'].create({
            'name': 'subtotals 1',
            'preceding_subtotal': "PRE GROUP 1",
            'sequence': 3,
            'pos_receipt_label': 'A',
        })
        cls.tax_group_sub2 = cls.env['account.tax.group'].create({
            'name': 'subtotals 2',
            'preceding_subtotal': "PRE GROUP 2",
            'sequence': 4,
            'pos_receipt_label': 'B',
        })
        cls.tax_group_sub3 = cls.env['account.tax.group'].create({
            'name': 'subtotals 3',
            'preceding_subtotal': "PRE GROUP 1", # same as sub1, on purpose
            'sequence': 5,
            'pos_receipt_label': 'C',
        })

        cls.tax_10 = cls.env['account.tax'].create({
            'name': "tax_10a",
            'amount_type': 'percent',
            'amount': 10.0,
        })
        cls.tax_16 = cls.env['account.tax'].create({
            'name': "tax_16",
            'amount_type': 'percent',
            'amount': 16.0,
        })
        cls.tax_23_1 = cls.env['account.tax'].create({
            'name': "tax_23_1",
            'amount_type': 'percent',
            'amount': 23.0,
        })
        cls.tax_23_2 = cls.env['account.tax'].create({
            'name': "tax_23_2",
            'amount_type': 'percent',
            'amount': 23.0,
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

        self.assert_document_tax_totals(document, {
            'amount_total': 3600.0,
            'amount_untaxed': 3000.0,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
                        'tax_group_amount': 200.0,
                        'tax_group_base_amount': 2000.0,
                        'tax_group_id': self.tax_group1.id,
                    },

                    {
                        'tax_group_name': self.tax_group2.name,
                        'tax_group_label': self.tax_group2.pos_receipt_label,
                        'tax_group_amount': 400.0,
                        'tax_group_base_amount': 2000.0,
                        'tax_group_id': self.tax_group2.id,
                    },
                ],
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 3000.0,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

        # Same but both are sharing the same tax group.

        tax_20.tax_group_id = self.tax_group1

        self.assert_document_tax_totals(document, {
            'amount_total': 3600,
            'amount_untaxed': 3000,
            'display_tax_base': False,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
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

        self.assert_document_tax_totals(document, {
            'amount_total': 1000,
            'amount_untaxed': 1000,
            'display_tax_base': False,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': tax_0.tax_group_id.name,
                        'tax_group_label': tax_0.tax_group_id.pos_receipt_label,
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
            'price_include_override': 'tax_included',
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

        self.assert_document_tax_totals(document, {
            'amount_total': 3620,
            'amount_untaxed': 3000,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
                        'tax_group_amount': 200,
                        'tax_group_base_amount': 2000,
                        'tax_group_id': self.tax_group1.id,
                    },

                    {
                        'tax_group_name': self.tax_group2.name,
                        'tax_group_label': self.tax_group2.pos_receipt_label,
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

        self.assert_document_tax_totals(document, {
            'amount_total': 3620,
            'amount_untaxed': 3000,
            'display_tax_base': False,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
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

        self.assert_document_tax_totals(document, {
            'amount_total': 2750,
            'amount_untaxed': 2000,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
                        'tax_group_amount': 450,
                        'tax_group_base_amount': 2300,
                        'tax_group_id': self.tax_group1.id,
                    },

                    {
                        'tax_group_name': self.tax_group2.name,
                        'tax_group_label': self.tax_group2.pos_receipt_label,
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

        self.assert_document_tax_totals(document, {
            'amount_total': 2750,
            'amount_untaxed': 2000,
            'display_tax_base': False,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
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

        self.assert_document_tax_totals(document, {
            'amount_total': 2846,
            'amount_untaxed': 2300,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
                        'tax_group_amount': 126,
                        'tax_group_base_amount': 300,
                        'tax_group_id': self.tax_group1.id,
                    },
                ],
                'PRE GROUP 1': [
                    {
                        'tax_group_name': self.tax_group_sub1.name,
                        'tax_group_label': self.tax_group_sub1.pos_receipt_label,
                        'tax_group_amount': 120,
                        'tax_group_base_amount': 1200,
                        'tax_group_id': self.tax_group_sub1.id,
                    },
                ],
                'PRE GROUP 2': [
                    {
                        'tax_group_name': self.tax_group_sub2.name,
                        'tax_group_label': self.tax_group_sub2.pos_receipt_label,
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

        self.assert_document_tax_totals(document, {
            'amount_total': 1867,
            'amount_untaxed': 1500,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
                        'tax_group_amount': 360,
                        'tax_group_base_amount': 1200,
                        'tax_group_id': self.tax_group1.id,
                    },
                ],

                'PRE GROUP 1': [
                    {
                        'tax_group_name': self.tax_group_sub1.name,
                        'tax_group_label': self.tax_group_sub1.pos_receipt_label,
                        'tax_group_amount': 42,
                        'tax_group_base_amount': 100,
                        'tax_group_id': self.tax_group_sub1.id,
                    },

                    {
                        'tax_group_name': self.tax_group_sub3.name,
                        'tax_group_label': self.tax_group_sub3.pos_receipt_label,
                        'tax_group_amount': 40,
                        'tax_group_base_amount': 400,
                        'tax_group_id': self.tax_group_sub3.id,
                    },
                ],

                'PRE GROUP 2': [
                    {
                        'tax_group_name': self.tax_group_sub2.name,
                        'tax_group_label': self.tax_group_sub2.pos_receipt_label,
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

        self.assert_document_tax_totals(document, {
            'amount_total': 63,
            'amount_untaxed': 100,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [{
                    'tax_group_name': self.tax_group1.name,
                    'tax_group_label': self.tax_group1.pos_receipt_label,
                    'tax_group_amount': 10,
                    'tax_group_base_amount': 100,
                    'tax_group_id': self.tax_group1.id,
                }],
                "Tax withholding": [{
                    'tax_group_name': self.tax_group_sub1.name,
                    'tax_group_label': self.tax_group_sub1.pos_receipt_label,
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
            (100.0, self.tax_10),
        ]
        run_case('round_per_line', lines, [15.45])
        run_case('round_globally', lines, [15.45])

        lines = [
            (54.45, self.tax_10),
            (600, self.tax_10),
            (-500, self.tax_10),
        ]
        run_case('round_per_line', lines, [15.45])
        # 5.445 + 60 - 50 = 15.444999999999993 ~= 15.45
        # 5.445 - 50 + 60 = 15.445 ~= 15.45
        # 5.445 + 10 = 15.445 ~= 15.45
        run_case('round_globally', lines, [15.45])

        lines = [
            (94.7, self.tax_23_1),
            (32.8, self.tax_23_2),
        ]
        run_case('round_per_line', lines, [29.32])
        run_case('round_globally', lines, [29.32])

    def test_invoice_foreign_currency_tax_totals(self):
        self.env['res.currency.rate'].create({
            'name': '2018-01-01',
            'rate': 0.2,
            'currency_id': self.other_currency.id,
            'company_id': self.env.company.id,
        })

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

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'currency_id': self.other_currency.id,
        })

        lines_data = [(100, tax_10), (300, tax_20)]
        invoice_lines_vals = [
            Command.create({
                'name': 'line',
                'display_type': 'product',
                'account_id': self.company_data['default_account_revenue'].id,
                'price_unit': amount,
                'tax_ids': [Command.set(taxes.ids)],
            })
            for amount, taxes in lines_data
        ]

        invoice['invoice_line_ids'] = invoice_lines_vals

        self.assert_document_tax_totals(invoice, {
            'amount_total': 470,
            'amount_total_company_currency': 2350,
            'amount_untaxed': 400,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
                        'tax_group_amount': 10,
                        'tax_group_base_amount': 100,
                        'tax_group_id': self.tax_group1.id,
                        'tax_group_amount_company_currency': 50,
                        'tax_group_base_amount_company_currency': 500,
                    },
                    {
                        'tax_group_name': self.tax_group2.name,
                        'tax_group_label': self.tax_group2.pos_receipt_label,
                        'tax_group_amount': 60,
                        'tax_group_base_amount': 300,
                        'tax_group_id': self.tax_group2.id,
                        'tax_group_amount_company_currency': 300,
                        'tax_group_base_amount_company_currency': 1500,
                    }
                ]
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 400,
                    'amount_company_currency': 2000,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

    def test_round_globally_price_included_tax(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        tax_1 = self.env['account.tax'].create({
            'name': "tax_1",
            'amount_type': 'fixed',
            'tax_group_id': self.tax_group1.id,
            'amount': 1.0,
            'include_base_amount': True,
            'price_include_override': 'tax_included',
        })
        tax_21 = self.env['account.tax'].create({
            'name': "tax_21",
            'amount_type': 'percent',
            'tax_group_id': self.tax_group2.id,
            'amount': 21.0,
            'price_include_override': 'tax_included',
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': f'line{i}',
                    'display_type': 'product',
                    'price_unit': 21.53,
                    'tax_ids': [Command.set((tax_1 + tax_21).ids)],
                })
                for i in range(2)
            ],
        })
        self.assert_document_tax_totals(invoice, {
            'amount_total': 43.05,
            'amount_untaxed': 33.58,
            'display_tax_base': True,
            'groups_by_subtotal': {
                'Untaxed Amount': [
                    {
                        'tax_group_name': self.tax_group1.name,
                        'tax_group_label': self.tax_group1.pos_receipt_label,
                        'tax_group_amount': 2,
                        'tax_group_base_amount': 33.59,
                        'tax_group_id': self.tax_group1.id,
                    },
                    {
                        'tax_group_name': self.tax_group2.name,
                        'tax_group_label': self.tax_group2.pos_receipt_label,
                        'tax_group_amount': 7.47,
                        'tax_group_base_amount': 35.59,
                        'tax_group_id': self.tax_group2.id,
                    }
                ]
            },
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'amount': 33.58,
                }
            ],
            'subtotals_order': ["Untaxed Amount"],
        })

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
            self.assertEqual(move.tax_totals['amount_total'], 545)

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
        moves.checked = False
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
            'currency_id': self.other_currency.id,
            'company_id': self.env.company.id,
        })
        for move_type in ['out_invoice', 'in_invoice']:
            move = self.env['account.move'].create({
                'move_type': move_type,
                'partner_id': self.partner_a.id,
                'invoice_date': '2023-01-01',
                'currency_id': self.other_currency.id,
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

    def test_tax_division_for_l10n_br(self):
        tax_groups = self.env['account.tax.group'].create([
            {
                'name': str(i),
                'sequence': 1,
            }
            for i in range(1, 6)
        ])
        taxes = self.env['account.tax'].create([
            {
                'name': f"division_{amount}",
                'amount_type': 'division',
                'amount': amount,
                'tax_group_id': tax_groups[0].id,
            }
            for amount in (5, 3, 0.65, 9, 15)
        ])

        # == Tax-excluded ==
        document = self._create_document_for_tax_totals_test([(32.33, taxes)])

        # Same tax group.
        with self.subTest("Tax-excluded / Same tax group"):
            self.assert_document_tax_totals(document, {
                'amount_total': 48.0,
                'amount_untaxed': 32.33,
                'display_tax_base': False,
                'groups_by_subtotal': {
                    "Untaxed Amount": [
                        {
                            'tax_group_name': taxes.tax_group_id.name,
                            'tax_group_label': taxes.tax_group_id.pos_receipt_label,
                            'tax_group_amount': 15.67,
                            'tax_group_base_amount': 32.33,
                            'tax_group_id': taxes.tax_group_id.id,
                        },
                    ],
                },
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'amount': 32.33,
                    }
                ],
                'subtotals_order': ["Untaxed Amount"],
            })

        # Multiple tax groups.
        for i, tax in enumerate(taxes):
            tax.tax_group_id = tax_groups[i]
        with self.subTest("Tax-excluded / Multiple tax groups"):
            self.assert_document_tax_totals(document, {
                'amount_total': 48.0,
                'amount_untaxed': 32.33,
                'display_tax_base': False,
                'groups_by_subtotal': {
                    "Untaxed Amount": [
                        {
                            'tax_group_name': tax_groups[0].name,
                            'tax_group_label': tax_groups[0].pos_receipt_label,
                            'tax_group_amount': 2.4,
                            'tax_group_base_amount': 32.33,
                            'tax_group_id': tax_groups[0].id,
                        },
                        {
                            'tax_group_name': tax_groups[1].name,
                            'tax_group_label': tax_groups[1].pos_receipt_label,
                            'tax_group_amount': 1.44,
                            'tax_group_base_amount': 32.33,
                            'tax_group_id': tax_groups[1].id,
                        },
                        {
                            'tax_group_name': tax_groups[2].name,
                            'tax_group_label': tax_groups[2].pos_receipt_label,
                            'tax_group_amount': 0.31,
                            'tax_group_base_amount': 32.33,
                            'tax_group_id': tax_groups[2].id,
                        },
                        {
                            'tax_group_name': tax_groups[3].name,
                            'tax_group_label': tax_groups[3].pos_receipt_label,
                            'tax_group_amount': 4.32,
                            'tax_group_base_amount': 32.33,
                            'tax_group_id': tax_groups[3].id,
                        },
                        {
                            'tax_group_name': tax_groups[4].name,
                            'tax_group_label': tax_groups[4].pos_receipt_label,
                            'tax_group_amount': 7.2,
                            'tax_group_base_amount': 32.33,
                            'tax_group_id': tax_groups[4].id,
                        },
                    ],
                },
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'amount': 32.33,
                    },
                ],
                'subtotals_order': ["Untaxed Amount"],
            })

        # == Tax-included ==
        taxes.write({'price_include_override': 'tax_included'})
        document = self._create_document_for_tax_totals_test([(48.0, taxes)])

        # Multiple tax groups.
        with self.subTest("Tax-included / Multiple tax groups"):
            self.assert_document_tax_totals(document, {
                'amount_total': 48.0,
                'amount_untaxed': 32.33,
                'display_tax_base': True,
                'groups_by_subtotal': {
                    "Untaxed Amount": [
                        {
                            'tax_group_name': tax_groups[0].name,
                            'tax_group_label': tax_groups[0].pos_receipt_label,
                            'tax_group_amount': 2.4,
                            'tax_group_base_amount': 48.0,
                            'tax_group_id': tax_groups[0].id,
                        },
                        {
                            'tax_group_name': tax_groups[1].name,
                            'tax_group_label': tax_groups[1].pos_receipt_label,
                            'tax_group_amount': 1.44,
                            'tax_group_base_amount': 48.0,
                            'tax_group_id': tax_groups[1].id,
                        },
                        {
                            'tax_group_name': tax_groups[2].name,
                            'tax_group_label': tax_groups[2].pos_receipt_label,
                            'tax_group_amount': 0.31,
                            'tax_group_base_amount': 48.0,
                            'tax_group_id': tax_groups[2].id,
                        },
                        {
                            'tax_group_name': tax_groups[3].name,
                            'tax_group_label': tax_groups[3].pos_receipt_label,
                            'tax_group_amount': 4.32,
                            'tax_group_base_amount': 48.0,
                            'tax_group_id': tax_groups[3].id,
                        },
                        {
                            'tax_group_name': tax_groups[4].name,
                            'tax_group_label': tax_groups[4].pos_receipt_label,
                            'tax_group_amount': 7.2,
                            'tax_group_base_amount': 48.0,
                            'tax_group_id': tax_groups[4].id,
                        },
                    ],
                },
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'amount': 32.33,
                    },
                ],
                'subtotals_order': ["Untaxed Amount"],
            })

        # Same tax group.
        taxes.tax_group_id = tax_groups[0]
        with self.subTest("Tax-included / Same tax group"):
            self.assert_document_tax_totals(document, {
                'amount_total': 48.0,
                'amount_untaxed': 32.33,
                'display_tax_base': True,
                'groups_by_subtotal': {
                    "Untaxed Amount": [
                        {
                            'tax_group_name': taxes.tax_group_id.name,
                            'tax_group_label': taxes.tax_group_id.pos_receipt_label,
                            'tax_group_amount': 15.67,
                            'tax_group_base_amount': 48.0,
                            'tax_group_id': taxes.tax_group_id.id,
                        },
                    ],
                },
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'amount': 32.33,
                    }
                ],
                'subtotals_order': ["Untaxed Amount"],
            })

    def test_display_tax_base_rounding(self):
        tax_19 = self.env['account.tax'].create({
            'name': "tax_19",
            'amount_type': 'percent',
            'amount': 19.0,
        })

        currency = self.setup_other_currency('CLP')
        self.company_data['company'].currency_id = currency.id
        self.company_data['company'].tax_calculation_rounding_method = 'round_globally'
        for amount in (23.0, 23.67):
            document = self._create_document_for_tax_totals_test([
                (amount, tax_19),
            ])
            document.currency_id = currency.id
            document.invalidate_model(fnames=['tax_totals'])
            self.assertFalse(document.tax_totals['display_tax_base'])
