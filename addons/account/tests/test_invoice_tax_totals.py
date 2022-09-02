# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
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
            'display_tax_base': False,
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
            'display_tax_base': False,
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
        })

        tax_20 = self.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
            'tax_group_id': self.tax_group1.id,
        })

        tax_30 = self.env['account.tax'].create({
            'name': "tax_30",
            'amount_type': 'percent',
            'amount': 30.0,
            'tax_group_id': self.tax_group2.id,
            'include_base_amount': True,
        })

        document = self._create_document_for_tax_totals_test([
            (1000, tax_10 + tax_20),
            (1000, tax_30 + tax_10),
        ])

        self.assertTaxTotals(document, {
            'amount_total': 2750,
            'amount_untaxed': 2000,
            'display_tax_base': False,
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
            'display_tax_base': False,
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
            'display_tax_base': False,
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
