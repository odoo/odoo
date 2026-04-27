# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE


@tagged('post_install_l10n', 'post_install', '-at_install')
class DenmarkSalesReportTest(AccountSalesReportCommon):
    @classmethod
    @AccountSalesReportCommon.setup_chart_template('dk')
    def setUpClass(cls):
        super().setUpClass()
        cls.company.update({
            'country_id': cls.env.ref('base.dk').id,
            'vat': 'DK58403288',
        })

    @freeze_time('2019-12-31')
    def test_ec_sales_report(self):
        goods_tax = self.env.ref(f"account.{self.company_data['company'].id}_tax_s2")
        triangular_tax = self.env.ref(f"account.{self.company_data['company'].id}_tax_s8")
        services_tax = self.env.ref(f"account.{self.company_data['company'].id}_tax_s3")

        self._create_invoices([
            (self.partner_a, goods_tax, 3000),
            (self.partner_a, goods_tax, 3000),
            (self.partner_a, services_tax, 7000),
            (self.partner_b, services_tax, 4000),
            (self.partner_b, triangular_tax, 2000),
        ])

        report = self.env.ref('l10n_dk_reports.denmark_ec_sales_report')
        options = report.get_options({'date': {'mode': 'range', 'filter': 'this_month'}})

        self.assertLinesValues(
            report._get_lines(options),
            [   0,                      1,                                  2,                      3,                                      4,                                      5,                                      6],
            [
                (self.partner_a.name,   self.partner_a.country_id.code,     self.partner_a.vat,     f'kr{NON_BREAKING_SPACE}6,000',      f'kr{NON_BREAKING_SPACE}7,000',      f'kr{NON_BREAKING_SPACE}0',          f'kr{NON_BREAKING_SPACE}13,000'),
                (self.partner_b.name,   self.partner_b.country_id.code,     self.partner_b.vat,     f'kr{NON_BREAKING_SPACE}0',          f'kr{NON_BREAKING_SPACE}4,000',      f'kr{NON_BREAKING_SPACE}2,000',      f'kr{NON_BREAKING_SPACE}6,000'),
                ('Total',               '',                                 '',                     f'kr{NON_BREAKING_SPACE}6,000',      f'kr{NON_BREAKING_SPACE}11,000',     f'kr{NON_BREAKING_SPACE}2,000',      f'kr{NON_BREAKING_SPACE}19,000'),
            ],
            options
        )

        correct_report = (
            '0,58403288,LIST,,,,,,\r\n'
            '2,0,2019-12-31,58403288,FR,23334175221,6000,0,7000\r\n'
            '2,1,2019-12-31,58403288,BE,0477472701,0,2000,4000\r\n'
            '10,2,19000,,,,,,\r\n'
        )

        gen_report = self.env[report.custom_handler_model_name].export_sales_report_to_csv(options)['file_content'].decode()

        self.assertEqual(gen_report, correct_report, "Error creating KVR")
