# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, tools
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAtSaftReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='at'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'city': 'Innsbruck',
            'zip': '6020',
            'company_registry': '123/4567',
            'vat': 'ATU12345675',
            'phone': '+43 512 321 54 76',
            'website': 'www.example.com',
            'email': 'info@example.com',
            'street': 'Am Bahnhof 10/A/4/15',
            'country_id': cls.env.ref('base.at').id,
            'l10n_at_oenace_code': 'OENACE-CODE',
            'l10n_at_profit_assessment_method': 'par_4_abs_1',
        })
        cls.env['res.partner'].create({
            'name': 'Mr Big CEO',
            'is_company': False,
            'phone': '+43 512 321 54 00',
            'email': 'big.CEO@example.com',
            'parent_id': cls.company_data['company'].partner_id.id,
        })

        (cls.partner_a + cls.partner_b).write({
            'street': 'Saftstraße 1',
            'city': 'Wien',
            'zip': '1600',
            'country_id': cls.env.ref('base.at').id,
            'phone': '+43 01 23 45 11',
        })

        cls.partner_a.company_registry = '123/4567a'
        cls.partner_b.company_registry = '123/4567b'

        cls.product_a.default_code = 'PA'
        cls.product_b.default_code = 'PB'

        # Create invoices

        cls.invoices = cls.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2019-01-01',
                'date': '2019-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_a.id,
                    'quantity': 5.0,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_sale'].ids)],
                })],
            },
            {
                'move_type': 'out_refund',
                'invoice_date': '2019-03-01',
                'date': '2019-03-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_a.id,
                    'quantity': 3.0,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_sale'].ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2019-06-30',
                'date': '2019-06-30',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [(0, 0, {
                    'account_id': cls.env['account.chart.template'].ref('chart_at_template_5000').id,
                    'product_id': cls.product_b.id,
                    'quantity': 10.0,
                    'price_unit': 800.0,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_purchase'].ids)],
                })],
            },
        ])
        cls.invoices.action_post()

    @freeze_time('2022-01-01')
    def test_saft_report_values(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))

        with tools.file_open("l10n_at_saft/tests/xml/expected_test_saft_report.xml", "rb") as expected_xml:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(self.env[report.custom_handler_model_name].with_context(skip_xsd=True).l10n_at_export_saft_to_xml(options)['file_content']),
                self.get_xml_tree_from_string(expected_xml.read()),
            )
