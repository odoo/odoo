# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=C0326

from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class GermanySalesReportTest(AccountSalesReportCommon):

    @classmethod
    @AccountSalesReportCommon.setup_chart_template('de_skr03')
    def setUpClass(cls):
        super().setUpClass()
        cls.company.update({
            'vat': 'DE123456788',
        })

    def _get_report_from_csv(self, report, options):
        csv_content = self.env['l10n_de.ec.sales.report.handler'].get_csvs(report, options)[0]
        lines = csv_content.strip().split('\n')
        headers = lines[2].split(',')
        return [
            {headers[i]: value.strip() for i, value in enumerate(line.split(','))}
            for line in lines[3:]
        ]

    @freeze_time('2019-12-31')
    def test_ec_sales_report(self):
        l_tax = self.env['account.tax'].search([
            ('name', '=', '0% EU D'),
            ('company_id', '=', self.company_data['company'].id)
        ])[0]
        t_tax = self.env['account.tax'].search([
            ('name', '=', '0% TT F'),
            ('company_id', '=', self.company_data['company'].id)
        ])[0]
        s_tax = self.env['account.tax'].search([
            ('name', '=', '0% EU'),
            ('company_id', '=', self.company_data['company'].id)
        ])[0]
        self._create_invoices([
            (self.partner_a, l_tax, 300),
            (self.partner_a, l_tax, 300),
            (self.partner_a, t_tax, 500),
            (self.partner_b, t_tax, 500),
            (self.partner_a, s_tax, 700),
            (self.partner_b, s_tax, 700),
        ])
        report = self.env.ref('l10n_de_reports.german_ec_sales_report')
        options = report.get_options({'date': {'mode': 'range', 'filter': 'this_month'}})
        lines = report._get_lines(options)
        self.assertLinesValues(
            lines,
            # pylint: disable=C0326
            #   Partner                country code,            VAT Number,             Tax   Amount
            [   0,                     1,                       2,                       3,    4],
            [
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'L',  f'600.00{NON_BREAKING_SPACE}€'),
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'D',  f'500.00{NON_BREAKING_SPACE}€'),
                (self.partner_a.name,  self.partner_a.vat[:2],  self.partner_a.vat[2:],  'S',  f'700.00{NON_BREAKING_SPACE}€'),
                (self.partner_b.name,  self.partner_b.vat[:2],  self.partner_b.vat[2:],  'D',  f'500.00{NON_BREAKING_SPACE}€'),
                (self.partner_b.name,  self.partner_b.vat[:2],  self.partner_b.vat[2:],  'S',  f'700.00{NON_BREAKING_SPACE}€'),
                ('Total',              '',                      '',                      '',   f'3,000.00{NON_BREAKING_SPACE}€'),
            ],
            options,
        )
        self.assertTrue(self.env['account.general.ledger.report.handler'].l10n_de_datev_export_to_zip(options).get('file_content'), 'Error creating CSV')

    @freeze_time('2019-12-31')
    def test_ec_sales_report_csv(self):
        """
        Amount should be integer
        "Feld "Summe": Volle Geldbetraege muessen als Ziffernfolge ohne Dezimaltrenner eingetragen werden. Negativen Geldbetraegen ist ein negatives Vorzeichen voran
        https://www.elster.de/eportal/helpGlobal?themaGlobal=zmdo_import_eop
        """
        l_tax = self.env['account.tax'].search([
            ('name', '=', '0% EU D'),
            ('company_id', '=', self.company_data['company'].id)
        ])[0]
        self._create_invoices([
            (self.partner_a, l_tax, 234.5),
        ])
        report = self.env.ref('l10n_de_reports.german_ec_sales_report')
        options = report.get_options({'date': {'mode': 'range', 'filter': 'this_month'}})
        self.assertEqual(self._get_report_from_csv(report, options)[0].get('Betrag (Euro)'), '235', 'Amount should be integer')
