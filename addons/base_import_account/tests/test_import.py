# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests import tagged
from odoo.tests.common import can_import
from odoo.tools import mute_logger, file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

@tagged('post_install', '-at_install')
class TestXLSXImport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        test_file = "account/static/xls/generic_import.xlsx"
        with file_open(test_file, "rb") as f:
            cls.file_content = f.read()

    @unittest.skipUnless(can_import('xlrd.xlsx'), "XLRD module not available")
    def test_xlsx_sheet_select(self):
        # test that the relevant sheet is automatically selected
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'res.partner',
            'file': self.file_content,
            'file_type': 'application/vnd.ms-excel'
        })

        preview = import_wizard.parse_preview({
            'has_headers': True,
        })
        self.assertIsNone(preview.get('error'))
        self.assertEqual(preview['options']['sheet'], 'Contacts')

    @unittest.skipUnless(can_import('xlrd.xlsx'), "XLRD module not available")
    def test_xlsx_mulirow_records(self):
        # test that a record can span multiple rows
        import_wizard = self.env['base_import.import'].create({
            'res_model': 'account.move',
            'file': self.file_content,
            'file_type': 'application/vnd.ms-excel'
        })

        preview = import_wizard.parse_preview({
            'has_headers': True,
        })
        preview['options']['name_create_enabled_fields'] = {'line_ids/account_id': True, 'journal_id': True}
        import_fields = import_wizard._convert_import_data(
            ['/'.join(match) for match in preview['matches'].values()],
            preview['options'])[1]

        result = import_wizard.with_company(self.env.company).execute_import(
            import_fields,
            preview['headers'],
            preview['options']
        )

        self.assertEqual(len(result['ids']), 3, 'Three Journal Entries should have been imported')

        for entry in self.env['account.move'].browse(result['ids']):
            self.assertGreater(len(entry.line_ids), 0)
            self.assertGreater(entry.amount_total, 0.0)

    @unittest.skipUnless(can_import('xlrd.xlsx'), "XLRD module not available")
    def test_xlsx_import_key_opening_balance(self):
        # test that the import key will update records with no xml_id
        existing_id = self.env['account.account'].with_context(import_file=True).name_create('550003 Existing Account')[0]

        import_wizard = self.env['base_import.import'].create({
            'res_model': 'account.account',
            'file': self.file_content,
            'file_type': 'application/vnd.ms-excel'
        })
        preview = import_wizard.parse_preview({
            'has_headers': True,
        })
        with mute_logger('odoo.sql_db'):
            result = import_wizard.execute_import(
                preview['headers'],
                preview['headers'],
                preview['options']
            )
        self.assertGreater(len(result['messages']), 0, "Error messages are expected, since import_keys are not specified")

        preview['options']['import_keys'] = ['code']
        result = import_wizard.execute_import(
            preview['headers'],
            preview['headers'],
            preview['options']
        )

        self.assertEqual(result['messages'], [], "The import should have been successful without error")

        existing_account = self.env['account.account'].browse(existing_id)
        self.assertEqual(len(result['ids']), 14, "14 Accounts should have been imported")
        self.assertEqual(existing_account.name, "Bank", "The existing account should have been updated")
        self.assertEqual(existing_account.current_balance, -3500.0, "The balance should have been updated")
