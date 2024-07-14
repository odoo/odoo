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
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass('de_skr03')

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'country_id': cls.env.ref('base.de').id,
            'vat': 'DE123456788',
        })
        return res

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
