# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account_saft.tests.common import TestSaftReport
from odoo.tests import tagged
from odoo.tests.common import test_xsd

from freezegun import freeze_time


class TestAtSaftReportCommon(TestSaftReport):
    @classmethod
    @TestSaftReport.setup_country('at')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'city': 'Innsbruck',
            'zip': '6020',
            'company_registry': '123/4567',
            'vat': 'ATU12345675',
            'phone': '+43 512 321 54 76',
            'website': 'www.example.com',
            'email': 'info@example.com',
            'street': 'Am Bahnhof 10/A/4/15',
            'l10n_at_oenace_code': 'OENACE-CODE',
            'l10n_at_profit_assessment_method': 'par_4_abs_1',
        })
        cls.partner_ceo = cls.env['res.partner'].create({
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
                'invoice_date': '2023-10-01',
                'date': '2023-10-01',
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
                'invoice_date': '2023-10-03',
                'date': '2023-10-03',
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
                'invoice_date': '2023-10-30',
                'date': '2023-10-30',
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

    def _l10n_at_saft_generate_report(self, options):
        with freeze_time('2023-11-01 10:00:00'):
            return self.report_handler.l10n_at_export_saft_to_xml(options)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAtSaftReport(TestAtSaftReportCommon):
    def test_saft_report_values(self):
        options = self._generate_options()
        report = self._l10n_at_saft_generate_report(options)
        self._report_compare_with_test_file(report, 'saft_report.xml')

    def test_saft_report_errors(self):
        company = self.company_data['company']
        company.write({
            'l10n_at_oenace_code': False,
            'l10n_at_profit_assessment_method': False,
        })
        self.partner_ceo.write({
            'phone': False,
            'mobile': False,
        })

        options = self._generate_options()
        with self.assertRaises(self.ReportException) as cm:
            self.report_handler.with_company(company).l10n_at_export_saft_to_xml(options)
        self.assertEqual(set(cm.exception.errors), {
            'missing_partner_phone_number',
            'missing_company_settings',
        })


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestAtSaftReportXmlValidity(TestAtSaftReportCommon):
    @test_xsd(url='https://www.bmf.gv.at/dam/jcr:3c407d8c-5657-47a7-90fc-e152d884fe42/SAF-T_AT_1.01.xsd')
    def test_saft_report_values(self):
        options = self._generate_options()
        return self._l10n_at_saft_generate_report(options)['file_content']
