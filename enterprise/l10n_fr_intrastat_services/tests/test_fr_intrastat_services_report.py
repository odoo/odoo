# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.l10n_fr_intrastat.tests.test_fr_intrastat_report import TestFRIntrastatReport


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFRIntrastatServicesReport(TestFRIntrastatReport):

    @classmethod
    @TestAccountReportsCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()
        italy = cls.env.ref('base.it')
        cls.report_services = cls.env.ref('account_intrastat_services.intrastat_report_services')
        cls.report_handler_services = cls.env['account.intrastat.services.report.handler']
        cls.product_service = cls.env['product.product'].create({
            'name': 'Personal service',
            'intrastat_code_id': cls.env.ref('account_intrastat.commodity_code_2023_25309050').id,
            'standard_price': 200.0,
            'type': 'service',
            'intrastat_origin_country_id': italy.id,
        })

        cls.invoice_with_service = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2023-10-25',
            'date': '2023-10-25',
            'intrastat_country_id': italy.id,
            'intrastat_transport_mode_id': cls.env.ref('account_intrastat.account_intrastat_transport_1').id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [
                Command.create({
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'product_id': cls.product_service.id,
                    'intrastat_transaction_id': cls.env.ref('account_intrastat.account_intrastat_transaction_11').id,
                    'quantity': 2,
                    'price_unit': 500,
                }),
                Command.create({
                    'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                    'product_id': cls.product_service.id,
                    'intrastat_transaction_id': cls.env.ref('account_intrastat.account_intrastat_transaction_11').id,
                    'quantity': 4,
                    'price_unit': 300,
                })],
        })

        cls.invoice_with_service.action_post()

    def _l10n_fr_intrastat_generate_report(self, options):
        with freeze_time('2023-11-01 10:00:00'):
            return self.report_handler_services.l10n_fr_intrastat_services_export_to_xml(options)

    def test_fr_intrastat_export_report_for_services(self):
        """ Test generating an XML export for services intrastat """
        options = self._generate_options(self.report_services)
        report_xml = self._l10n_fr_intrastat_generate_report(options)
        self._report_compare_with_test_file(report_xml, 'services_export.xml')
