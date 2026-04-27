# -*- coding: utf-8 -*-
from freezegun import freeze_time

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo import Command, fields
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestF29Reports(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('cl')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.write({
            'country_id': cls.env.ref('base.cl').id,
            'l10n_cl_sii_taxpayer_type': '1',
            'vat': 'CL762012243',
        })
        cl_account_310115 = cls.env['account.account'].search([('company_ids', '=', cls.company_data['company'].id), ('code', '=', '310115')]).id
        cl_account_410230 = cls.env['account.account'].search([('company_ids', '=', cls.company_data['company'].id), ('code', '=', '410230')]).id
        cl_purchase_tax = cls.env['account.tax'].search([('name', '=', '19% F A'), ('company_id', '=', cls.company_data['company'].id)])

        invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2022-01-01',
            'date': '2022-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'account_id': cl_account_310115,
                    'product_id': cls.product_a.id,
                    'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                })
            ],
        })
        vendor_bill = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2022-01-01',
            'date': '2022-01-01',
            'l10n_latam_document_type_id': cls.env['l10n_latam.document.type'].search([
                ('code', '=', '46'),
                ('country_id.code', '=', 'CL')
            ]).id,
            'l10n_latam_document_number': 10,
            'invoice_line_ids': [
                (0, 0, {
                    'account_id': cl_account_410230,
                    'product_id': cls.product_a.id,
                    'tax_ids': [Command.set(cl_purchase_tax.ids)],
                    'quantity': 3.0,
                    'price_unit': 400.0,
                })
            ],
        })
        invoice.action_post()
        vendor_bill.action_post()

    @freeze_time('2022-01-31')
    def test_whole_report(self):
        report = self.env.ref('l10n_cl_reports.account_financial_report_f29')
        options = self._generate_options(report, date_from=fields.Date.from_string('2022-01-01'), date_to=fields.Date.from_string('2022-01-31'))
        # pylint: disable=bad-whitespace
        self.assertLinesValues(
            report._get_lines(options),
            # pylint: disable=C0326
            #   Line Title                                                              Value
            [   0,                                                                             1],
            [
                ('Taxable Sales Base',                                                        ''),
                ('Net Sales Taxed VAT',                                                   1000.0),
                ('Exempt Sales',                                                             0.0),
                ('Exports',                                                                  0.0),  # exports sales
                ('Proposed Ratio Factor (%)',                                             '0.0%'),
                ('Total Sales',                                                           1000.0),
                ('Taxes Paid on Sale',                                                        ''),
                ('VAT Tax Debit',                                                          190.0),  # 19% tax of 1000
                ('Tax Base Purchases',                                                        ''),
                ('Net Taxable Purchases Recoverable VAT',                                 1200.0),
                ('Net Purchases Taxed VAT Common Use',                                       0.0),
                ('Purchases Non-recoverable VAT',                                            0.0),
                ('Supermarket Shopping',                                                     0.0),
                ('Purchases of fixed assets',                                                0.0),
                ('Purchases Not Taxed With VAT',                                             0.0),
                ('Total Net Purchases',                                                   1200.0),
                ('Taxes Paid on Purchase',                                                    ''),
                ('VAT Paid Purchases Recoverable',                                           0.0),
                ('VAT Common Use',                                                           0.0),
                ('VAT Shopping Supermarket',                                                 0.0),
                ('VAT Purchases of Fixed Assets Destined for Exempt Sales',                228.0),  # 19% tax of 3*400
                ('VAT Purchases Fixed Assets Common Use',                                    0.0),
                ('VAT Purchases of Non-recoverable Fixed Assets',                            0.0),
                ('VAT Base Tax Credit Affected by FP',                                        ''),
                ('Recoverable VAT',                                                          0.0),
                ('VAT Common Use',                                                           0.0),
                ('VAT Purchases Supermarket Common Use',                                     0.0),
                ('VAT Purchases Fixed Assets Earmarked Sales Exempt Sales',                  0.0),
                ('VAT Purchases Fixed Assets Sales Common Use',                              0.0),
                ('VAT Purchases Fixed Assets Non Recoverable Sales',                         0.0),
                ('Totals',                                                                    ''),
                ('VAT Tax Credit',                                                         228.0),
                ('VAT Payable (Negative: Balance in Favor of the Company)',                -38.0),  # 190-228
                ('Remaining CF',                                                             0.0),
                ('Workers\' Tax',                                                            0.0),
                ('Withholding Fees',                                                         0.0),
                ('PPM rate (%)',                                                          '0.0%'),
                ('PPM',                                                                      0.0),
                ('Total Taxes for the Period (Negative: Balance in Favor of the Company)', -38.0),
            ],
            options,
        )

    @freeze_time('2022-01-31')
    def test_report_external_values(self):
        report = self.env.ref('l10n_cl_reports.account_financial_report_f29')
        options = self._generate_options(report, date_from=fields.Date.from_string('2022-01-01'), date_to=fields.Date.from_string('2022-01-31'))
        fpp_rate = self.env['account.report.external.value'].create({
            'company_id': self.env.company.id,
            'target_report_expression_id': self.env.ref('l10n_cl_reports.account_financial_report_f29_line_0104_balance').id,
            'name': 'Manual value',
            'date': fields.Date.from_string('2022-01-31'),
            'value': 10,
        })
        ppm_rate = self.env['account.report.external.value'].create({
            'company_id': self.env.company.id,
            'target_report_expression_id': self.env.ref('l10n_cl_reports.account_financial_report_f29_line_0606_balance').id,
            'name': 'Manual value',
            'date': fields.Date.from_string('2022-01-31'),
            'value': 25,
        })
        # pylint: disable=bad-whitespace
        self.assertLinesValues(
            report._get_lines(options),
            # pylint: disable=C0326
            #   Line Title                                                              Value
            [   0,                                                                                1],
            [
                ('Taxable Sales Base',                                                           ''),
                ('Net Sales Taxed VAT',                                                      1000.0),
                ('Exempt Sales',                                                                0.0),
                ('Exports',                                                                     0.0),  # exports sales
                ('Proposed Ratio Factor (%)',                                               '10.0%'),  # FPP rate
                ('Total Sales',                                                              1000.0),
                ('Taxes Paid on Sale',                                                           ''),
                ('VAT Tax Debit',                                                             190.0),  # 19% tax of 1000
                ('Tax Base Purchases',                                                           ''),
                ('Net Taxable Purchases Recoverable VAT',                                    1200.0),
                ('Net Purchases Taxed VAT Common Use',                                          0.0),
                ('Purchases Non-recoverable VAT',                                               0.0),
                ('Supermarket Shopping',                                                        0.0),
                ('Purchases of fixed assets',                                                   0.0),
                ('Purchases Not Taxed With VAT',                                                0.0),
                ('Total Net Purchases',                                                      1200.0),
                ('Taxes Paid on Purchase',                                                       ''),
                ('VAT Paid Purchases Recoverable',                                              0.0),
                ('VAT Common Use',                                                              0.0),
                ('VAT Shopping Supermarket',                                                    0.0),
                ('VAT Purchases of Fixed Assets Destined for Exempt Sales',                   228.0),  # 19% tax of 3*400
                ('VAT Purchases Fixed Assets Common Use',                                       0.0),
                ('VAT Purchases of Non-recoverable Fixed Assets',                               0.0),
                ('VAT Base Tax Credit Affected by FP',                                           ''),
                ('Recoverable VAT',                                                             0.0),
                ('VAT Common Use',                                                              0.0),
                ('VAT Purchases Supermarket Common Use',                                        0.0),
                ('VAT Purchases Fixed Assets Earmarked Sales Exempt Sales',                    23.0),  # FPP rate 10% of 228 (rounded because of currency decimal_places of 0)
                ('VAT Purchases Fixed Assets Sales Common Use',                                 0.0),
                ('VAT Purchases Fixed Assets Non Recoverable Sales',                            0.0),
                ('Totals',                                                                       ''),
                ('VAT Tax Credit',                                                            228.0),
                ('VAT Payable (Negative: Balance in Favor of the Company)',                   -38.0),  # 190-228
                ('Remaining CF',                                                                0.0),
                ('Workers\' Tax',                                                               0.0),
                ('Withholding Fees',                                                            0.0),
                ('PPM rate (%)',                                                            '25.0%'),  # PPM rate
                ('PPM',                                                                       250.0),  # PPM rate 25% of 1000
                ('Total Taxes for the Period (Negative: Balance in Favor of the Company)',    212.0),  # 250 - 38
            ],
            options,
        )
        fpp_rate.write({'value': 20})
        ppm_rate.write({'value': 30})
        self.assertLinesValues(
            report._get_lines(options),
            # pylint: disable=C0326
            #   Line Title                                                              Value
            [   0,                                                                                   1],
            [
                ('Taxable Sales Base',                                                              ''),
                ('Net Sales Taxed VAT',                                                         1000.0),
                ('Exempt Sales',                                                                   0.0),
                ('Exports',                                                                        0.0),  # exports sales
                ('Proposed Ratio Factor (%)',                                                  '20.0%'),  # FPP rate
                ('Total Sales',                                                                 1000.0),
                ('Taxes Paid on Sale',                                                              ''),
                ('VAT Tax Debit',                                                                190.0),  # 19% tax of 1000
                ('Tax Base Purchases',                                                              ''),
                ('Net Taxable Purchases Recoverable VAT',                                       1200.0),
                ('Net Purchases Taxed VAT Common Use',                                             0.0),
                ('Purchases Non-recoverable VAT',                                                  0.0),
                ('Supermarket Shopping',                                                           0.0),
                ('Purchases of fixed assets',                                                      0.0),
                ('Purchases Not Taxed With VAT',                                                   0.0),
                ('Total Net Purchases',                                                         1200.0),
                ('Taxes Paid on Purchase',                                                          ''),
                ('VAT Paid Purchases Recoverable',                                                 0.0),
                ('VAT Common Use',                                                                 0.0),
                ('VAT Shopping Supermarket',                                                       0.0),
                ('VAT Purchases of Fixed Assets Destined for Exempt Sales',                      228.0),  # 19% tax of 3*400
                ('VAT Purchases Fixed Assets Common Use',                                          0.0),
                ('VAT Purchases of Non-recoverable Fixed Assets',                                  0.0),
                ('VAT Base Tax Credit Affected by FP',                                              ''),
                ('Recoverable VAT',                                                                0.0),
                ('VAT Common Use',                                                                 0.0),
                ('VAT Purchases Supermarket Common Use',                                           0.0),
                ('VAT Purchases Fixed Assets Earmarked Sales Exempt Sales',                       46.0),  # FPP rate 20% of 228 (rounded because of currency decimal_places of 0)
                ('VAT Purchases Fixed Assets Sales Common Use',                                    0.0),
                ('VAT Purchases Fixed Assets Non Recoverable Sales',                               0.0),
                ('Totals',                                                                          ''),
                ('VAT Tax Credit',                                                               228.0),
                ('VAT Payable (Negative: Balance in Favor of the Company)',                      -38.0),  # 190-228
                ('Remaining CF',                                                                   0.0),
                ('Workers\' Tax',                                                                  0.0),
                ('Withholding Fees',                                                               0.0),
                ('PPM rate (%)',                                                               '30.0%'),  # PPM rate
                ('PPM',                                                                          300.0),  # PPM rate 30% of 1000
                ('Total Taxes for the Period (Negative: Balance in Favor of the Company)',       262.0),  # 300 - 38
            ],
            options,
        )
