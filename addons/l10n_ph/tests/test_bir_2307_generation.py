# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import xlrd
import base64

from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBIR2307Generation(TestPhCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # 10% Withholding Tax
        purchase_10_wc516 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_10_wc516')

        cls.invoice = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2020-01-15',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test line',
                    'quantity': 1.0,
                    'price_unit': 100,
                    'tax_ids': purchase_10_wc516,
                })
            ]
        })
        cls.invoice.action_post()

        cls.partner = cls.env['res.partner'].create({
            'vat': '123-456-789-001',
            'branch_code': '001',
            'name': 'Jose Mangahas Cuyegkeng',
            'first_name': 'Jose',
            'middle_name': 'Mangahas',
            'last_name': 'Cuyegkeng',
            'street': "250 Amorsolo Street",
            'city': "Manila",
            'country_id': cls.env.ref('base.ph').id,
            'zip': "+900–1-096",
        })

        cls.partner_a.write({
            'vat': '123-456-789-001',
            'branch_code': '001',
            'name': 'JMC Company',
            'street': "250 Amorsolo Street",
            'city': "Manila",
            'country_id': cls.env.ref('base.ph').id,
            'zip': "+900–1-096",
            'is_company': True,
        })

        cls.other_currency = cls.setup_other_currency('EUR', rates=[('2017-01-01', 2)])

    def test_bir_2307_company(self):
        """ Test the report """
        wizard_action = self.invoice.action_open_l10n_ph_2307_wizard()
        context = wizard_action['context']
        wizard = self.env['l10n_ph_2307.wizard'].with_context(context).create({})
        wizard.action_generate()

        bir_2307 = base64.b64decode(wizard.xls_file)

        # 2: Build the expected values
        expected_values = {
            # Header
            0: ['Reporting_Month', 'Vendor_TIN', 'branchCode', 'companyName', 'surName', 'firstName', 'middleName', 'address', 'zip_code', 'nature', 'ATC', 'income_payment', 'ewt_rate', 'tax_amount'],
            # Row
            1: ['01/15/2020', '123456789', '001', 'JMC Company', '', '', '', '250 Amorsolo Street, Manila, Philippines', '+900–1-096', 'WC516 - Commission/rebates/discounts', 'WC516', 100.0, 10.0, 10.0],
        }

        report_file = io.BytesIO(bir_2307)
        xls = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xls.sheet_by_index(0)
        for row, values in expected_values.items():
            row_values = sheet.row_values(row)
            for row_value, expected_value in zip(row_values, values):
                self.assertEqual(row_value, expected_value)

    def test_01_no_atc(self):
        """ Ensure that generating the file on a document where no taxes has an ATC set will work, although gives an empty file. """
        tax = self._create_tax('10% VAT', 10)
        bill = self.init_invoice(
            move_type='in_invoice',
            amounts=[100],
            taxes=tax,
        )
        bill.action_post()
        wizard = self.env['l10n_ph_2307.wizard'].with_context(default_moves_to_export=bill.ids).create({})
        wizard.action_generate()
        report_file = io.BytesIO(base64.b64decode(wizard.xls_file))
        xl = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xl.sheet_by_index(0)

        result = []
        for row in range(1, sheet.nrows):
            result.append(sheet.row_values(row))
        self.assertEqual(result, [])

    def test_02_simple_atc(self):
        """ Ensure that generating the file on a document with a single ATC tax and check the results. """
        tax = self._create_tax('10% ATC', -10, l10n_ph_atc='WI010')
        bill = self.init_invoice(
            move_type='in_invoice',
            amounts=[1000],
            taxes=tax,
            partner=self.partner,
            invoice_date='2025-01-01',
        )
        bill.action_post()
        wizard = self.env['l10n_ph_2307.wizard'].with_context(default_moves_to_export=bill.ids).create({})
        wizard.action_generate()
        report_file = io.BytesIO(base64.b64decode(wizard.xls_file))
        xl = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xl.sheet_by_index(0)

        result = []
        for row in range(1, sheet.nrows):
            result.append(sheet.row_values(row))
        self.assertEqual(result, [
            ['01/01/2025', '123456789', '001', '', 'Cuyegkeng', 'Jose', 'Mangahas', '250 Amorsolo Street, Manila, Philippines', '+900–1-096', '', 'WI010', 1000.0, 10.0, 100.0]
        ])

    def test_03_atc_affected_by_vat(self):
        """ Ensure that generating the file on a document where the ATC tax is affected works as expected. """
        vat = self._create_tax('15% VAT', 15, include_base_amount=True)
        atc = self._create_tax('10% ATC', -10, l10n_ph_atc='WI010', is_base_affected=True)
        atc.description = '10% ATC'
        bill = self.init_invoice(
            move_type='in_invoice',
            amounts=[1000],
            taxes=(vat | atc),
            partner=self.partner,
            invoice_date='2025-01-01',
        )
        bill.action_post()
        wizard = self.env['l10n_ph_2307.wizard'].with_context(default_moves_to_export=bill.ids).create({})
        wizard.action_generate()
        report_file = io.BytesIO(base64.b64decode(wizard.xls_file))
        xl = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xl.sheet_by_index(0)

        result = []
        for row in range(1, sheet.nrows):
            result.append(sheet.row_values(row))
        self.assertEqual(result, [
            ['01/01/2025', '123456789', '001', '', 'Cuyegkeng', 'Jose', 'Mangahas', '250 Amorsolo Street, Manila, Philippines', '+900–1-096', '10% ATC', 'WI010', 1150.0, 10.0, 115.0]
        ])

    def test_04_multi_currency(self):
        """ Ensure that generating the file on a document of another currency than the company's gives the correct result. """
        tax = self._create_tax('10% ATC', -10, l10n_ph_atc='WI010')
        bill = self.init_invoice(
            move_type='in_invoice',
            amounts=[2000],
            taxes=tax,
            partner=self.partner_a,
            invoice_date='2025-01-01',
            currency=self.other_currency,
        )
        bill.action_post()
        wizard = self.env['l10n_ph_2307.wizard'].with_context(default_moves_to_export=bill.ids).create({})
        wizard.action_generate()
        report_file = io.BytesIO(base64.b64decode(wizard.xls_file))
        xl = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xl.sheet_by_index(0)

        result = []
        for row in range(1, sheet.nrows):
            result.append(sheet.row_values(row))
        # We expect the values in company currency in the file.
        self.assertEqual(result, [
            ['01/01/2025', '123456789', '001', 'JMC Company', '', '', '', '250 Amorsolo Street, Manila, Philippines', '+900–1-096', '', 'WI010', 1000.0, 10.0, 100.0]
        ])

    @classmethod
    def _create_tax(
        cls,
        name,
        amount,
        amount_type="percent",
        type_tax_use="sale",
        tax_exigibility="on_invoice",
        **kwargs,
    ):
        vals = {
            "name": name,
            "amount": amount,
            "amount_type": amount_type,
            "type_tax_use": type_tax_use,
            "tax_exigibility": tax_exigibility,
            "invoice_repartition_line_ids": [
                Command.create(
                    {
                        "factor_percent": 100,
                        "repartition_type": "base",
                    }
                ),
                Command.create(
                    {
                        "factor_percent": 100,
                        "repartition_type": "tax",
                    }
                ),
            ],
            "refund_repartition_line_ids": [
                Command.create(
                    {
                        "factor_percent": 100,
                        "repartition_type": "base",
                    }
                ),
                Command.create(
                    {
                        "factor_percent": 100,
                        "repartition_type": "tax",
                    }
                ),
            ],
            **kwargs,
        }
        return cls.env["account.tax"].create(vals)
