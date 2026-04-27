# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.l10n_ph.tests.common import TestPhCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSawtQapGeneration(TestAccountReportsCommon, TestPhCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        vat_sale_wc139 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_sale_wc139')  # 10% WC139 - Commission of service fees
        vat_sale_wi157 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_sale_wi157')  # 2% WI157 - Supplier of services
        vat_sale_wi100 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_sale_wi100')  # 5% WI100 - Gross rental of property
        vat_sale_wc140 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_sale_wc140')  # 15% WC140 - Commission of service fees
        vat_sale_12 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_sale_vat_12')    # 12% VAT

        vat_purchase_wc139 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_wc139')
        vat_purchase_wi157 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_wi157')
        vat_purchase_wi100 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_wi100')
        vat_purchase_wc140 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_wc140')
        vat_purchase_12 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_vat_12')

        cls.partner_a.write({
            'first_name': 'John',
            'middle_name': 'Doe',
            'last_name': 'Smith',
        })
        invoice_data = [
            # Sales
            ('out_invoice', cls.partner_a, '2024-07-15', [
                (250, vat_sale_wc139),
                (200, vat_sale_wi157),
            ]),
            ('out_invoice', cls.partner_b, '2024-07-15', [(500, vat_sale_wi100)]),
            ('out_invoice', cls.partner_c, '2024-07-16', [(300, vat_sale_wc140)]),
            ('out_invoice', cls.partner_c, '2024-07-15', [(300, vat_sale_12)]),     # No ATC code so ignored in the report
            # Purchases
            ('in_invoice', cls.partner_a, '2024-07-15', [
                (250, vat_purchase_wc139),
                (200, vat_purchase_wi157),
            ]),
            ('in_invoice', cls.partner_b, '2024-07-15', [(500, vat_purchase_wi100)]),
            ('in_invoice', cls.partner_c, '2024-07-16', [(300, vat_purchase_wc140)]),
            ('in_invoice', cls.partner_c, '2024-07-15', [(300, vat_purchase_12)]),  # No ATC code so ignored in the report
        ]

        invoice_vals = []
        for move_type, partner, invoice_date, lines in invoice_data:
            invoice_vals.append({
                'move_type': move_type,
                'invoice_date': invoice_date,
                'partner_id': partner.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Test line',
                        'quantity': 1.0,
                        'price_unit': amount,
                        'tax_ids': tax,
                    }) for amount, tax in lines
                ]
            })
        invoices = cls.env['account.move'].create(invoice_vals)
        invoices.action_post()

    def test_sawt(self):
        report = self.env.ref('l10n_ph_reports.sawt_report')
        options = self._generate_options(report, fields.Date.from_string('2024-07-01'), fields.Date.from_string('2024-07-31'))
        report_handler = self.env['l10n_ph.sawt.report.handler']

        sawt = report_handler.export_sawt_qap(options)['file_content']
        # 2: Build the expected values
        expected_row_values = {
            # Header
            0: ['Reporting_Month', 'Vendor_TIN', 'branchCode', 'companyName',          'surName', 'firstName', 'middleName', 'address',                                  'zip_code', 'nature',                                  'ATC',   'income_payment', 'ewt_rate', 'tax_amount'],  # noqa: E241
            # Row
            1: ['07/15/2024',      '789456123',  '789',        '',                     'Smith',   'John',      'Doe',        '9 Super Street, Super City, Philippines',  '8888',     '10% WC139 - Commission of service fees',  'WC139',  250.0,            10.0,       25.0],         # noqa: E241
            2: ['07/15/2024',      '789456123',  '789',        '',                     'Smith',   'John',      'Doe',        '9 Super Street, Super City, Philippines',  '8888',     '2% WI157 - Supplier of services',         'WI157',  200.0,            2.0,        4.0],         # noqa: E241
            3: ['07/15/2024',      '789456123',  '456',        'Test Partner Company', '',        '',          '',           '10 Super Street, Super City, Philippines', '8888',     '5% WI100 - Gross rental of property',     'WI100',  500.0,            5.0,        25.0],         # noqa: E241
            4: ['07/16/2024',      '789456123',  '456',        'Test Partner Company', '',        '',          '',           '10 Super Street, Super City, Philippines', '8888',     '15% WC140 - Commission of service fees',  'WC140',  300.0,            15.0,       45.0],         # noqa: E241
        }

        self._test_xlsx_file(sawt, expected_row_values)

    def test_qap(self):
        report = self.env.ref('l10n_ph_reports.qap_report')
        options = self._generate_options(report, fields.Date.from_string('2024-07-01'), fields.Date.from_string('2024-07-31'))
        report_handler = self.env['l10n_ph.qap.report.handler']

        qap = report_handler.export_sawt_qap(options)['file_content']
        # 2: Build the expected values
        expected_row_values = {
            # Header
            0: ['Reporting_Month', 'Vendor_TIN', 'branchCode', 'companyName',          'surName', 'firstName', 'middleName', 'address',                                  'zip_code', 'nature',                                  'ATC',   'income_payment', 'ewt_rate', 'tax_amount'],  # noqa: E241
            # Row
            1: ['07/15/2024',      '789456123',  '789',        '',                     'Smith',   'John',      'Doe',        '9 Super Street, Super City, Philippines',  '8888',     '10% WC139 - Commission of service fees',  'WC139',  250.0,            10.0,       25.0],         # noqa: E241
            2: ['07/15/2024',      '789456123',  '789',        '',                     'Smith',   'John',      'Doe',        '9 Super Street, Super City, Philippines',  '8888',     '2% WI157 - Supplier of services',         'WI157',  200.0,            2.0,        4.0],         # noqa: E241
            3: ['07/15/2024',      '789456123',  '456',        'Test Partner Company', '',        '',          '',           '10 Super Street, Super City, Philippines', '8888',     '5% WI100 - Gross rental of property',     'WI100',  500.0,            5.0,        25.0],         # noqa: E241
            4: ['07/16/2024',      '789456123',  '456',        'Test Partner Company', '',        '',          '',           '10 Super Street, Super City, Philippines', '8888',     '15% WC140 - Commission of service fees',  'WC140',  300.0,            15.0,       45.0],         # noqa: E241
        }

        self._test_xlsx_file(qap, expected_row_values)

    def test_withholding_tax(self):
        """ Test exporting the SAWT when a withholding tax on payment is involved.
        Note: without the l10n_account_withholding_tax module, we wouldn't have any withholding tax records to show.
        """
        if self.env.ref('base.module_l10n_account_withholding_tax').state != 'installed':
            self.skipTest("This test requires the 'Withholding Tax on Payment' module to be installed.")

        withholding_sequence = self.env['ir.sequence'].create({
            'implementation': 'no_gap',
            'name': 'Withholding Sequence',
            'padding': 4,
            'number_increment': 1,
        })
        wth_tax = self.env['account.chart.template'].with_company(self.company_data["company"]).ref('l10n_ph_tax_sale_wi011')
        wth_tax.write({
            'is_withholding_tax_on_payment': True,
            'withholding_sequence_id': withholding_sequence.id,
        })
        invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
            'invoice_date': '2024-07-16',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test line',
                    'quantity': 1.0,
                    'price_unit': 1000,
                    'tax_ids': wth_tax,
                })
            ]
        })
        invoice.action_post()
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()
        self.env.flush_all()

        report = self.env.ref('l10n_ph_reports.sawt_report')
        options = self._generate_options(report, fields.Date.from_string('2024-07-01'), fields.Date.from_string('2024-07-31'))
        report_handler = self.env['l10n_ph.sawt.report.handler']

        sawt = report_handler.export_sawt_qap(options)['file_content']
        # 2: Build the expected values
        expected_row_values = {
            # Header
            0: ['Reporting_Month', 'Vendor_TIN', 'branchCode', 'companyName',          'surName', 'firstName', 'middleName', 'address',                                  'zip_code', 'nature',                                  'ATC',   'income_payment', 'ewt_rate', 'tax_amount'],  # noqa: E241
            # Row
            1: ['07/15/2024',      '789456123',  '789',        '',                     'Smith',   'John',      'Doe',        '9 Super Street, Super City, Philippines',  '8888',     '10% WC139 - Commission of service fees',  'WC139',  250.0,            10.0,       25.0],         # noqa: E241
            2: ['07/15/2024',      '789456123',  '789',        '',                     'Smith',   'John',      'Doe',        '9 Super Street, Super City, Philippines',  '8888',     '2% WI157 - Supplier of services',         'WI157',  200.0,            2.0,        4.0],          # noqa: E241
            3: ['07/15/2024',      '789456123',  '456',        'Test Partner Company', '',        '',          '',           '10 Super Street, Super City, Philippines', '8888',     '5% WI100 - Gross rental of property',     'WI100',  500.0,            5.0,        25.0],         # noqa: E241
            4: ['07/16/2024',      '789456123',  '456',        'Test Partner Company', '',        '',          '',           '10 Super Street, Super City, Philippines', '8888',     '15% WC140 - Commission of service fees',  'WC140',  300.0,            15.0,       45.0],         # noqa: E241
            5: ['07/16/2024',      '789456123',  '789',        '',                     'Smith',   'John',      'Doe',        '9 Super Street, Super City, Philippines',  '8888',     '10% WI011 - Prof Fees',                   'WI011',  1000.0,           10.0,       100.0],        # noqa: E241
        }

        self._test_xlsx_file(sawt, expected_row_values)
