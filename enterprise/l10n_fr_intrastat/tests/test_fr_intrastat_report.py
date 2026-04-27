# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.account_reports.models.account_report import AccountReportFileDownloadException

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFRIntrastatReport(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()
        italy = cls.env.ref('base.it')
        cls.company_data['company'].write({
            'vat': 'FR23334175221',
            'siret': '2333417522155555',
            'l10n_fr_intrastat_envelope_id': 'D090',
            'intrastat_region_id': cls.env.ref('l10n_fr_intrastat.intrastat_region_01').id,
        })
        cls.report = cls.env.ref('account_intrastat.intrastat_report')
        cls.report_handler = cls.env['account.intrastat.report.handler']
        cls.partner_a = cls.env['res.partner'].create({
            'name': "Miskatonic University",
            'country_id': italy.id,
            'vat': 'IT12345670017',
        })

        cls.product_aeroplane = cls.env['product.product'].create({
            'name': 'Dornier Aeroplane',
            'intrastat_code_id': cls.env.ref('account_intrastat.commodity_code_2018_88023000').id,
            'intrastat_supplementary_unit_amount': 1,
            'weight': 3739,
            'intrastat_origin_country_id': italy.id,
        })
        cls.product_samples = cls.env['product.product'].create({
            'name': 'Interesting Antarctic Rock and Soil Specimens',
            'intrastat_code_id': cls.env.ref('account_intrastat.commodity_code_2023_25309050').id,
            'weight': 19,
            'intrastat_origin_country_id': italy.id,
        })
        cls.inwards_vendor_bill = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2023-10-15',
            'date': '2023-10-15',
            'intrastat_country_id': italy.id,
            'intrastat_transport_mode_id': cls.env.ref('account_intrastat.account_intrastat_transport_1').id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                'intrastat_transaction_id': cls.env.ref('account_intrastat.account_intrastat_transaction_11').id,
                'product_id': cls.product_samples.id,
                'quantity': 42,
                'price_unit': 555.44,
            })],
        })
        cls.outwards_customer_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2023-10-15',
            'date': '2023-10-15',
            'intrastat_country_id': italy.id,
            'intrastat_transport_mode_id': cls.env.ref('account_intrastat.account_intrastat_transport_1').id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                'product_id': cls.product_aeroplane.id,
                'intrastat_transaction_id': cls.env.ref('account_intrastat.account_intrastat_transaction_11').id,
                'quantity': 4,
                'price_unit': 3000.45,
            })],
        })

        cls.outwards_customer_invoice2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2023-10-25',
            'date': '2023-10-25',
            'intrastat_country_id': italy.id,
            'intrastat_transport_mode_id': cls.env.ref('account_intrastat.account_intrastat_transport_1').id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [(0, 0, {
                'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                'product_id': cls.product_aeroplane.id,
                'intrastat_transaction_id': cls.env.ref('account_intrastat.account_intrastat_transaction_11').id,
                'quantity': 2,
                'price_unit': 10050.1,
            })],
        })

        cls.inwards_vendor_bill.action_post()
        cls.outwards_customer_invoice.action_post()
        cls.outwards_customer_invoice2.action_post()

    def _generate_options(self, report, wizard_options=None):
        # EXTENDS account_intrastat
        options = super()._generate_options(report, date_from='2023-10-01', date_to='2023-10-31')
        if wizard_options:
            wizard = self.env['l10n_fr_intrastat.export.wizard'].create(wizard_options)
            options['l10n_fr_intrastat_wizard_id'] = wizard.id
        arrivals, dispatches = options['intrastat_type']
        arrivals['selected'], dispatches['selected'] = arrivals, dispatches
        return options

    def _l10n_fr_intrastat_generate_report(self, options):
        with freeze_time('2023-11-01 10:00:00'):
            return self.report_handler.l10n_fr_intrastat_export_to_xml(options)

    def test_fr_intrastat_export_both_export_types_and_flows(self):
        """ Test generating an XML export when the export type contains both documents (statistical survey and
        vat summary statement) and both export flow for the EMEBI export (arrivals and dispatches)"""
        options = self._generate_options(self.report, {
            'export_type': 'statistical_survey_and_vat_summary_statement',
            'emebi_flow': 'arrivals_and_dispatches',
        })
        report = self._l10n_fr_intrastat_generate_report(options)
        self._report_compare_with_test_file(report, 'both_types_flows.xml')

    def test_fr_intrastat_export_statistical_survey_with_arrival_emebi(self):
        """ Test generating an XML export when the export type contains only the statistical survey and the export
        flow for the EMEBI export is only arrivals"""
        options = self._generate_options(self.report, {
            'export_type': 'statistical_survey',
            'emebi_flow': 'arrivals',
        })
        report = self._l10n_fr_intrastat_generate_report(options)
        self._report_compare_with_test_file(report, 'survey_arrival_emebi.xml')

    def test_fr_intrastat_export_vat_summary_stmt(self):
        """ Test generating an XML export when the export type contains only the vat summary statement"""
        options = self._generate_options(self.report, {
            'export_type': 'vat_summary_statement',
            'emebi_flow': 'arrivals_and_dispatches',  # Does not matter in case of vat_summary_statement
        })
        report = self._l10n_fr_intrastat_generate_report(options)
        self._report_compare_with_test_file(report, 'vat_summary_stmt.xml')

    def test_fr_intrastat_export_errors(self):
        self.company_data['company'].siret = False
        self.outwards_customer_invoice.intrastat_transport_mode_id = False
        self.outwards_customer_invoice.line_ids[0].update({
            "intrastat_transaction_id": False,
            "intrastat_product_origin_country_id": False,
        })
        self.product_aeroplane.intrastat_code_id = False
        self.company_data['company'].write({
            'siret': False,
            'intrastat_region_id': False,
        })
        options = self._generate_options(self.report, {
            'export_type': 'statistical_survey_and_vat_summary_statement',
            'emebi_flow': 'arrivals_and_dispatches',
        })

        try:
            self._l10n_fr_intrastat_generate_report(options)
        except AccountReportFileDownloadException as arfde:
            self.assertEqual(set(arfde.errors.keys()), {
                'company_vat_or_siret_missing',
                'move_lines_transaction_code_missing',
                'move_lines_country_of_origin_missing',
                'move_lines_transport_code_missing',
                'products_commodity_code_missing',
                'settings_region_id_missing',
            })
            for error_key, error in arfde.errors.items():
                self.assertEqual({'action', 'action_text', 'message'}, set(error.keys()))
                self.assertTrue('name' in error['action'])
