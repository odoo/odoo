# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDKIntrastatReport(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_chart_template('dk')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].country_id = cls.env.ref('base.dk')
        belgium = cls.env.ref('base.be')
        cls.report = cls.env.ref('account_intrastat.intrastat_report')
        cls.report_handler = cls.env['account.intrastat.report.handler']

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'SUPER BELGIAN PARTNER',
            'street': 'Rue du Paradis, 10',
            'zip': '6870',
            'city': 'Eghezee',
            'country_id': belgium.id,
            'phone': '061928374',
            'vat': 'BE0897223670',
        })

        cls.product_rocket = cls.env['product.product'].create({
            'name': 'rocket',
            'intrastat_code_id': cls.env.ref('account_intrastat.commodity_code_2018_88023000').id,
            'intrastat_supplementary_unit_amount': 1,
            'weight': 5000,
            'intrastat_origin_country_id': cls.env.ref('base.es').id,
        })

        cls.inwards_vendor_bill = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2024-05-15',
            'date': '2024-05-15',
            'intrastat_country_id': belgium.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [Command.create({
                'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                'intrastat_transaction_id': cls.env.ref('account_intrastat.account_intrastat_transaction_11').id,
                'product_id': cls.product_rocket.id,
                'quantity': 10,
                'price_unit': 30000,
            })]
        })

        cls.outwards_customer_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2024-05-15',
            'date': '2024-05-15',
            'intrastat_country_id': belgium.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [Command.create({
                'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
                'product_id': cls.product_rocket.id,
                'intrastat_transaction_id': cls.env.ref('account_intrastat.account_intrastat_transaction_11').id,
                'quantity': 4,
                'price_unit': 30000,
            })]
        })

        cls.inwards_vendor_bill.action_post()
        cls.outwards_customer_invoice.action_post()

    def test_dk_intrastat_arrivals_xlsx(self):
        """ Test that data provided for the xlsx export of intrastat report with Danish
        company will correspond to the expected format in case only arrivals are requested
        """
        options = self._generate_options(self.report, '2024-05-01', '2024-05-31', default_options={'unfold_all': True, 'export_mode': 'file'})

        options['intrastat_type'][0]['selected'] = True   # arrivals
        options['intrastat_type'][1]['selected'] = False  # dispatches

        options_arrivals = self.report_handler._dk_prepare_options(options, self.report_handler._dk_get_col_order('arrivals'), 'arrivals')
        arrivals_only_lines = self.report_handler._dk_intrastat_xlsx_get_data(self.report, options_arrivals)

        expected_lines = [
            [
                'CN8 goods code', 'Nature of transaction', 'Partner country (Country of Destination/Country of Consignment)',
                'Net Mass', 'Supplementary Units', 'Invoice Value', 'Declarant Ref. No. (optional)'
            ],
            [
                '88023000', '11', 'BE', '50000.0', '10.0', '300000', 'BILL/2024/05/0001'
            ],
        ]

        self.assertListEqual(arrivals_only_lines, expected_lines)

    def test_dk_intrastat_dispatches_xlsx(self):
        """ Test that data provided for the xlsx export of intrastat report with Danish
        company will correspond to the expected format in case only dispatches are requested
        """
        options = self._generate_options(self.report, '2024-05-01', '2024-05-31', default_options={'unfold_all': True, 'export_mode': 'file'})

        options['intrastat_type'][0]['selected'] = False  # arrivals
        options['intrastat_type'][1]['selected'] = True   # dispatches

        options_dispatches = self.report_handler._dk_prepare_options(options, self.report_handler._dk_get_col_order('dispatches'), 'dispatches')
        dispatches_only_lines = self.report_handler._dk_intrastat_xlsx_get_data(self.report, options_dispatches)

        expected_lines = [
            [
                'CN8 goods code', 'Nature of transaction', 'Partner country (Country of Destination/Country of Consignment)',
                'Net Mass', 'Supplementary Units', 'Invoice Value', 'Declarant Ref. No. (optional)',
                'Partner VAT No.', 'Country of Origin'
            ],
            [
                '88023000', '11', 'BE', '20000.0', '4.0', '120000', 'INV/2024/00001', 'BE0897223670', 'ES'
            ],
        ]

        self.assertListEqual(dispatches_only_lines, expected_lines)
