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

        # 1% Withholding Tax
        vat_purchase_wc640 = cls.env.ref(f'account.{cls.company_data["company"].id}_l10n_ph_tax_purchase_wc640')

        cls.invoice = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2020-01-15',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test line',
                    'quantity': 1.0,
                    'price_unit': 100,
                    'tax_ids': vat_purchase_wc640,
                })
            ]
        })
        cls.invoice.action_post()

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
            0: ['Reporting_Month', 'Vendor_TIN', 'branchCode', 'companyName', 'surName', 'firstName', 'middleName', 'address', 'nature', 'ATC', 'income_payment', 'ewt_rate', 'tax_amount'],
            # Row
            1: ['01/15/2020', '789456123', '789', 'Test Partner', '', '', '', '9 Super Street, Super City, Philippines', 'Test line', 'WC640', 100.0, 1.0, 1.0],
        }

        report_file = io.BytesIO(bir_2307)
        xls = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xls.sheet_by_index(0)
        for row, values in expected_values.items():
            row_values = sheet.row_values(row)
            for row_value, expected_value in zip(row_values, values):
                self.assertEqual(row_value, expected_value)
