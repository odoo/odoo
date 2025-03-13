# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

import xlrd
import io
import base64


@tagged("post_install_l10n", "post_install", "-at_install")
class TestBir2037(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_ph.l10n_ph_chart_template"):
        super().setUpClass(chart_template_ref=chart_template_ref)

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

    def test_01_no_atc(self):
        """ Ensure that generating the file on a document where no taxes has an ATC set will work, although gives an empty file. """
        tax = self._create_tax('10% VAT', 10)
        bill = self._create_invoice(
            move_type='in_invoice',
            invoice_amount=100,
            taxes=tax,
        )
        bill.action_post()
        wizard = self.env['l10n_ph_2307.wizard'].with_context(default_moves_to_export=bill.ids).create({})
        wizard.action_generate()
        report_file = io.BytesIO(base64.b64decode(wizard.generate_xls_file))
        xl = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xl.sheet_by_index(0)

        result = []
        for row in range(1, sheet.nrows):
            result.append(sheet.row_values(row))
        self.assertEqual(result, [])

    def test_02_simple_atc(self):
        """ Ensure that generating the file on a document with a single ATC tax and check the results. """
        tax = self._create_tax('10% ATC', -10, l10n_ph_atc='WI010')
        bill = self._create_invoice(
            move_type='in_invoice',
            invoice_amount=1000,
            taxes=tax,
            partner_id=self.partner.id,
            date_invoice='2025-01-01',
        )
        bill.action_post()
        wizard = self.env['l10n_ph_2307.wizard'].with_context(default_moves_to_export=bill.ids).create({})
        wizard.action_generate()
        report_file = io.BytesIO(base64.b64decode(wizard.generate_xls_file))
        xl = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xl.sheet_by_index(0)

        result = []
        for row in range(1, sheet.nrows):
            result.append(sheet.row_values(row))
        self.assertEqual(result, [
            ['01/01/2025', '123456789', '001', 'Jose Mangahas Cuyegkeng', 'Cuyegkeng', 'Jose', 'Mangahas', '250 Amorsolo Street, Manila, Philippines', 'product that cost 1000', 'WI010', 1000.0, -10.0, -100.0]
        ])

    def test_03_atc_affected_by_vat(self):
        """ Ensure that generating the file on a document where the ATC tax is affected works as expected. """
        vat = self._create_tax('15% VAT', 15, include_base_amount=True)
        atc = self._create_tax('10% ATC', -10, l10n_ph_atc='WI010', is_base_affected=True)
        bill = self._create_invoice(
            move_type='in_invoice',
            invoice_amount=1000,
            taxes=(vat | atc),
            partner_id=self.partner.id,
            date_invoice='2025-01-01',
        )
        bill.action_post()
        wizard = self.env['l10n_ph_2307.wizard'].with_context(default_moves_to_export=bill.ids).create({})
        wizard.action_generate()
        report_file = io.BytesIO(base64.b64decode(wizard.generate_xls_file))
        xl = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xl.sheet_by_index(0)

        result = []
        for row in range(1, sheet.nrows):
            result.append(sheet.row_values(row))
        self.assertEqual(result, [
            ['01/01/2025', '123456789', '001', 'Jose Mangahas Cuyegkeng', 'Cuyegkeng', 'Jose', 'Mangahas', '250 Amorsolo Street, Manila, Philippines', 'product that cost 1000', 'WI010', 1150.0, -10.0, -115.0]
        ])

    def test_04_multi_currency(self):
        """ Ensure that generating the file on a document of another currency than the company's gives the correct result. """
        tax = self._create_tax('10% ATC', -10, l10n_ph_atc='WI010')
        bill = self._create_invoice(
            move_type='in_invoice',
            invoice_amount=2000,
            taxes=tax,
            partner_id=self.partner.id,
            date_invoice='2025-01-01',
            currency_id=self.currency_data['currency'].id,
        )
        bill.action_post()
        wizard = self.env['l10n_ph_2307.wizard'].with_context(default_moves_to_export=bill.ids).create({})
        wizard.action_generate()
        report_file = io.BytesIO(base64.b64decode(wizard.generate_xls_file))
        xl = xlrd.open_workbook(file_contents=report_file.read())
        sheet = xl.sheet_by_index(0)

        result = []
        for row in range(1, sheet.nrows):
            result.append(sheet.row_values(row))
        # We expect the values in company currency in the file.
        self.assertEqual(result, [
            ['01/01/2025', '123456789', '001', 'Jose Mangahas Cuyegkeng', 'Cuyegkeng', 'Jose', 'Mangahas', '250 Amorsolo Street, Manila, Philippines', 'product that cost 2000', 'WI010', 1000.0, -10.0, -100.0]
        ])
