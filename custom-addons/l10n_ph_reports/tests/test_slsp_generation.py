# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import xlrd

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from odoo import Command, fields
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSLSPGeneration(TestAccountReportsCommon):
    # pylint: disable=C0326

    @classmethod
    def setUpClass(cls, chart_template_ref="ph"):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Start by setting up test partners/company

        cls.company_data['company'].write({
            'name': 'Test Company',
            'street': '8 Super Street',
            'city': 'Super City',
            'zip': '8888',
            'country_id': cls.env.ref('base.ph').id,
            'vat': '123-456-789-123',
        })
        cls.partner_a.write({
            'name': 'Test Partner',
            'street': '9 Super Street',
            'city': 'Super City',
            'zip': '8888',
            'country_id': cls.env.ref('base.ph').id,
            'vat': '789-456-123-789',
        })
        cls.partner_b.write({
            'name': 'Test Partner Company',
            'street': '10 Super Street',
            'city': 'Super City',
            'zip': '8888',
            'country_id': cls.env.ref('base.ph').id,
            'is_company': True,
            'vat': '789-456-123-456',
        })
        cls.partner_c = cls.env['res.partner'].create({
            'name': 'Test Partner Company Member',
            'property_payment_term_id': cls.pay_terms_b.id,
            'property_supplier_payment_term_id': cls.pay_terms_b.id,
            'property_account_position_id': cls.fiscal_pos_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].copy().id,
            'property_account_payable_id': cls.company_data['default_account_payable'].copy().id,
            'street': '11 Super Street',
            'city': 'Super City',
            'zip': '8888',
            'country_id': cls.env.ref('base.ph').id,
            'vat': '789-456-123-123',
            'company_id': False,
            'parent_id': cls.partner_b.id,
        })

        # Gather taxes that we will use to build our moves. We need a variety of them as we want to test the different cases.
        vat_exempt_sale = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_sale_vat_exempt')
        vat_zr_sale = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_sale_vat_zero_rated')
        vat_sale_12 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_sale_vat_12')

        vat_exempt_purchase = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_vat_exempt')
        vat_zr_purchase = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_vat_zero_rated')
        vat_purchase_12 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_vat_12')
        vat_purchase_service_12 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_vat_12_service')
        vat_purchase_capital_12 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_vat_12_capital')

        invoice_data = [
            # Sales
            ('out_invoice', cls.partner_c, '2020-02-16', [(300, vat_sale_12)]),
            ('out_invoice', cls.partner_c, '2020-02-15', [(300, False)]),  # No tax grids so ignored in the report
            ('out_invoice', cls.partner_a, '2020-01-15', [
                (250, vat_sale_12),
                (200, vat_exempt_sale),
            ]),
            ('out_invoice', cls.partner_b, '2020-01-15', [
                (500, vat_sale_12),
                (100, vat_zr_sale),
            ]),
            # Purchases
            ('in_invoice', cls.partner_c, '2020-02-16', [(300, vat_purchase_12)]),
            ('in_invoice', cls.partner_a, '2020-02-15', [(300, False)]),  # No tax grids so ignored in the report
            ('in_invoice', cls.partner_a, '2020-01-15', [
                (250, vat_purchase_12),
                (200, vat_exempt_purchase),
                (50, vat_purchase_service_12),
            ]),
            ('in_invoice', cls.partner_b, '2020-01-15', [
                (500, vat_purchase_12),
                (100, vat_zr_purchase),
                (250, vat_purchase_capital_12),
            ]),
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

    def _test_xlsx_file(self, file_content, expected_values):
        """ Takes in the binary content of a xlsx file and a dict of expected values.
        It will then parse the file in order to compare the values with the expected ones.
        The expected values dict format is:
        'row_number': ['cell_1_val', 'cell_2_val', ...]

        :param file_content: The binary content of the xlsx file
        :param expected_values: The dict of expected values
        """
        report_file = io.BytesIO(file_content)
        xlsx = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xlsx.sheet_by_index(0)

        for row, values in expected_values.items():
            row_values = sheet.row_values(row)
            for row_value, expected_value in zip(row_values, values):
                self.assertEqual(row_value, expected_value)

    def test_sl_sales(self):
        """ Test the report """
        # 1: Get the file data
        report = self.env.ref('l10n_ph_reports.sls_report')
        options = self._generate_options(report, fields.Date.from_string('2020-01-01'), fields.Date.from_string('2020-02-29'))
        report_handler = self.env['l10n_ph.slsp.report.handler']

        sls = report_handler.export_slsp(options)['file_content']
        # 2: Build the expected values
        expected_row_values = {
            # Header
            0: ['SALES TRANSACTION'],
            1: ['RECONCILIATION OF LISTING FOR ENFORCEMENT'],
            5: ['TIN:', '123-456-789-123'],
            6: ['OWNER\'S NAME:', 'Test Company'],
            7: ['OWNER\'S TRADE NAME:', 'Test Company'],
            8: ['OWNER\'S ADDRESS:', '8 Super Street\nSuper City  8888\nPhilippines'],

            # Data headers
            10: ['TAXABLE', 'TAXPAYER', 'REGISTER NAME', 'NAME OF CUSTOMER', 'CUSTOMER\'S ADDRESS', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF'],
            11: ['MONTH', 'IDENTIFICATION', '', '(Last Name, First Name, Middle Name)', '', 'GROSS SALES', 'EXEMPT SALES', 'ZERO-RATED SALES', 'TAXABLE SALES', 'OUTPUT TAX', 'GROSS TAXABLE SALES'],
            12: ['', 'NUMBER'],

            # Moves data
            14: ['2020-02-29', '789-456-123-456', 'Test Partner Company', 'Test Partner Company Member', '10 Super Street\nSuper City  8888\nPhilippines', 300.0, '',    '',    300.0, 36.0, 336.0],
            15: ['2020-01-31', '789-456-123-789', '',                     'Test Partner',                '9 Super Street\nSuper City  8888\nPhilippines',  450.0, 200.0, '',    250.0, 30.0, 280.0],
            16: ['2020-01-31', '789-456-123-456', 'Test Partner Company', '',                            '10 Super Street\nSuper City  8888\nPhilippines', 600.0, '',    100.0, 500.0, 60.0, 560.0],

            # Totals
            18: ['Grand total:', '', '', '', '', 1350.0, 200.0, 100.0, 1050.0, 126.0, 1176.0],

            # End
            20: ['END OF REPORT'],
        }
        # 3. Test the file
        self._test_xlsx_file(sls, expected_row_values)

    def test_sl_purchase(self):
        """ Test the report """
        # 1: Open the wizard
        # 1: Get the file data
        report = self.env.ref('l10n_ph_reports.slp_report')
        options = self._generate_options(report, fields.Date.from_string('2020-01-01'), fields.Date.from_string('2020-02-29'))
        report_handler = self.env['l10n_ph.slsp.report.handler']

        slp = report_handler.export_slsp(options)['file_content']
        # 3: Build the expected values
        expected_row_values = {
            # Header
            0: ['PURCHASE TRANSACTION'],
            1: ['RECONCILIATION OF LISTING FOR ENFORCEMENT'],
            5: ['TIN:', '123-456-789-123'],
            6: ['OWNER\'S NAME:', 'Test Company'],
            7: ['OWNER\'S TRADE NAME:', 'Test Company'],
            8: ['OWNER\'S ADDRESS:', '8 Super Street\nSuper City  8888\nPhilippines'],

            # Data headers
            10: ['TAXABLE', 'TAXPAYER', 'REGISTER NAME', 'NAME OF SUPPLIER', 'SUPPLIER\'S ADDRESS', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF', 'AMOUNT OF'],
            11: ['MONTH', 'IDENTIFICATION', '', '(Last Name, First Name, Middle Name)', '', 'GROSS PURCHASE', 'EXEMPT PURCHASE', 'ZERO-RATED PURCHASE', 'TAXABLE PURCHASE', 'PURCHASE OF SERVICES', 'PURCHASE OF CAPITAL GOODS', 'PURCHASE OF OTHER THAN CAPITAL GOODS', 'INPUT TAX', 'GROSS TAXABLE PURCHASE'],
            12: ['', 'NUMBER'],

            # Partners data
            14: ['2020-02-29', '789-456-123-456', 'Test Partner Company', 'Test Partner Company Member', '10 Super Street\nSuper City  8888\nPhilippines', 300.0, '',    '',    300.0, '',   '',    300.0, 36.0, 336.0],
            15: ['2020-01-31', '789-456-123-789', '',                     'Test Partner',                '9 Super Street\nSuper City  8888\nPhilippines',  500.0, 200.0, '',    300.0, 50.0, '',    250.0, 36.0, 336.0],
            16: ['2020-01-31', '789-456-123-456', 'Test Partner Company', '',                            '10 Super Street\nSuper City  8888\nPhilippines', 850.0, '',    100.0, 750.0, '',   250.0, 500.0, 90.0, 840.0],

            # Totals
            18: ['Grand total:', '', '', '', '', 1650.0, 200.0, 100.0, 1350.0, 50.0, 250.0, 1050.0, 162.0, 1512.0],

            # End
            20: ['END OF REPORT'],
        }
        # 4. Test the file
        self._test_xlsx_file(slp, expected_row_values)
