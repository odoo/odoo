# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests import tagged
from odoo.tests.common import can_import
from odoo.tools import mute_logger
from odoo.modules.module import get_module_resource

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

@tagged('post_install', '-at_install')
class TestXLSXImport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        xls_file_path = get_module_resource('account', 'static', 'xls', 'generic_import.xlsx')
        cls.file_content = open(xls_file_path, 'rb').read()

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
        preview['options']['name_create_enabled_fields'] = {'line_ids/account_id':True}
        input_file_data, import_fields = import_wizard._convert_import_data(
            ['/'.join(match) for match in preview['matches'].values()],
            preview['options'])

        result = import_wizard.with_company(self.env.company).execute_import(
            import_fields,
            preview['headers'],
            preview['options']
        )

        self.assertEqual(len(result['ids']), 3, 'Three Journal Entries should have been imported')

        for record in input_file_data:
            journal_entry = self.env['account.move'].search([('name', '=', record[1])])
            journal_item = journal_entry.line_ids.filtered(lambda l: l.name == record[4])
            self.assertEqual(journal_item.account_id.code, record[5].split(' ', 1)[0], f'Account code {journal_item.account_id.code} does not match {record[5]}')
            self.assertEqual(str(journal_item.debit or ''), str(float(record[6]) if record[6] else ''), f'journal item debit {journal_item.debit} does not match {record[6]}')
            self.assertEqual(str(journal_item.credit or ''), str(float(record[7]) if record[7] else ''), f'journal item credit {journal_item.credit} does not match {record[7]}')

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
        self.assertEqual(len(result['ids']), 12, '12 Accounts should have been imported')
        self.assertEqual(existing_account.name, "Bank", "The existing account should have been updated")
        self.assertEqual(existing_account.current_balance, -3500.0, "The balance should have been updated")
