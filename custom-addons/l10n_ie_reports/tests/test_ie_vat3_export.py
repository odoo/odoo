# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo import fields
from odoo import tools


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestIeVat3Export(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ie'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'name': 'Irish Company',
            'vat': 'IE1519572A',
            'country_id': cls.env.ref('base.ie').id,
        })

        cls.partner_a.write({
            'name': 'Irish Partner',
            'is_company': True,
            'country_id': cls.env.ref('base.ie').id,
        })
        cls.partner_b.write({
            'name': 'French Partner',
            'is_company': True,
            'country_id': cls.env.ref('base.fr').id,
        })
        cls.partner_c = cls.env['res.partner'].create({
            'name': 'English Partner',
            'is_company': True,
            'country_id': cls.env.ref('base.uk').id,
        })

        tax_sale_goods_23 = cls.env['account.chart.template'].ref('ie_tax_sale_goods_23')
        tax_purchase_goods_23 = cls.env['account.chart.template'].ref('ie_tax_purchase_goods_23')
        tax_sale_goods_eu_0 = cls.env['account.chart.template'].ref('ie_tax_sale_goods_eu_0')
        tax_purchase_goods_eu_23 = cls.env['account.chart.template'].ref('ie_tax_purchase_goods_eu_23')
        tax_sale_services_eu_0 = cls.env['account.chart.template'].ref('ie_tax_sale_services_eu_0')
        tax_purchase_services_eu_23 = cls.env['account.chart.template'].ref('ie_tax_purchase_services_eu_23')
        tax_postponed_accounting = cls.env['account.chart.template'].ref('ie_tax_purchase_ex_goods_pa_0')

        # Create invoices
        cls.invoices = cls.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-01-01',
                'date': '2023-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, tax_sale_goods_23.ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-01-11',
                'date': '2023-01-11',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 300.0,
                    'tax_ids': [(6, 0, tax_purchase_goods_23.ids)],
                })],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-01-21',
                'date': '2023-01-21',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 400.0,
                    'tax_ids': [(6, 0, tax_sale_goods_eu_0.ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-02-01',
                'date': '2023-02-01',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 550.0,
                    'tax_ids': [(6, 0, tax_purchase_goods_eu_23.ids)],
                })],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-02-05',
                'date': '2023-02-05',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 780.0,
                    'tax_ids': [(6, 0, tax_sale_services_eu_0.ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-02-10',
                'date': '2023-02-10',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 1010.0,
                    'tax_ids': [(6, 0, tax_purchase_services_eu_23.ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-02-15',
                'date': '2023-02-15',
                'partner_id': cls.partner_c.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 1490.0,
                    'tax_ids': [(6, 0, tax_postponed_accounting.ids)],
                })],
            },
        ])
        cls.invoices.action_post()

    def test_vat3_export(self):
        report = self.env.ref('l10n_ie.l10n_ie_tr')
        options = self._generate_options(report, fields.Date.from_string('2023-01-01'), fields.Date.from_string('2023-02-28'))
        stringified_xml = self.env[report.custom_handler_model_name].l10n_ie_export_vat3_to_xml(options)['file_content']
        with tools.file_open('l10n_ie_reports/tests/expected_xmls/vat3.xml', 'rb') as expected_xml_file:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(stringified_xml),
                self.get_xml_tree_from_string(expected_xml_file.read()),
            )
