# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestInvoiceTaxAmountByGroup(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.tax_group1 = cls.env['account.tax.group'].create({'name': '1'})
        cls.tax_group2 = cls.env['account.tax.group'].create({'name': '2'})

    def assertAmountByTaxGroup(self, invoice, expected_values):
        current_values = [(x[6], x[2], x[1]) for x in invoice.amount_by_group]
        self.assertEqual(current_values, expected_values)

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

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, (tax_10 + tax_20).ids)],
                }),
                (0, 0, {
                    'name': 'line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, tax_10.ids)],
                }),
                (0, 0, {
                    'name': 'line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, tax_20.ids)],
                }),
            ]
        })

        self.assertAmountByTaxGroup(invoice, [
            (self.tax_group1.id, 2000.0, 200.0),
            (self.tax_group2.id, 2000.0, 400.0),
        ])

        # Same but both are sharing the same tax group.

        tax_20.tax_group_id = self.tax_group1
        invoice.invalidate_cache(['amount_by_group'])

        self.assertAmountByTaxGroup(invoice, [
            (self.tax_group1.id, 3000.0, 600.0),
        ])

    def test_zero_tax_lines(self):
        tax_0 = self.env['account.tax'].create({
            'name': "tax_0",
            'amount_type': 'percent',
            'amount': 0.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, tax_0.ids)],
                }),
            ]
        })

        self.assertAmountByTaxGroup(invoice, [
            (tax_0.tax_group_id.id, 1000.0, 0.0),
        ])

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

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1100.0,
                    'tax_ids': [(6, 0, (tax_10 + tax_20).ids)],
                }),
                (0, 0, {
                    'name': 'line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1100.0,
                    'tax_ids': [(6, 0, tax_10.ids)],
                }),
                (0, 0, {
                    'name': 'line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, tax_20.ids)],
                }),
            ]
        })

        self.assertAmountByTaxGroup(invoice, [
            (self.tax_group1.id, 2000.0, 200.0),
            (self.tax_group2.id, 2100.0, 420.0),
        ])

        # Same but both are sharing the same tax group.

        tax_20.tax_group_id = self.tax_group1
        invoice.invalidate_cache(['amount_by_group'])

        self.assertAmountByTaxGroup(invoice, [
            (self.tax_group1.id, 3000.0, 620.0),
        ])

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

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, (tax_10 + tax_20).ids)],
                }),
                (0, 0, {
                    'name': 'line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, (tax_30 + tax_10).ids)],
                }),
            ]
        })

        self.assertAmountByTaxGroup(invoice, [
            (self.tax_group1.id, 2300.0, 450.0),
            (self.tax_group2.id, 1000.0, 300.0),
        ])

        # Same but both are sharing the same tax group.

        tax_30.tax_group_id = self.tax_group1
        invoice.invalidate_cache(['amount_by_group'])

        self.assertAmountByTaxGroup(invoice, [
            (self.tax_group1.id, 2000.0, 750.0),
        ])
