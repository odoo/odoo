# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests import tagged
from odoo.tests.common import can_import
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

@tagged("post_install", "-at_install")
class TestXLSXImport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        coa_file = "account_base_import/static/src/xls/coa_import.xlsx"
        journal_items_file = "account_base_import/static/src/xls/journal_items_import.xlsx"
        duplicate_journals_file = "account_base_import/static/src/xls/duplicate_journals_import.xlsx"
        with file_open(coa_file, "rb") as f:
            cls.coa_file_content = f.read()
        with file_open(journal_items_file, "rb") as f:
            cls.journal_items_file_content = f.read()
        with file_open(duplicate_journals_file, "rb") as f:
            cls.duplicate_journals_file_content = f.read()

    def _create_save_import(self, res_model, file):
        import_wizard = self.env["base_import.import"].create({
            "res_model": res_model,
            "file": file,
            "file_type": "application/vnd.ms-excel"
        })
        preview = import_wizard.parse_preview({
            "has_headers": True,
        })
        preview["options"]["name_create_enabled_fields"] = {
            "journal_id": True,
            "account_id": True,
            "partner_id": True,
        }

        return import_wizard.with_company(self.env.company).execute_import(
            preview["headers"],
            preview["headers"],
            preview["options"]
        )

    @unittest.skipUnless(can_import("xlrd.xlsx"), "XLRD module not available")
    def test_account_xlsx_import(self):
        existing_id = self.env["account.account"].with_context(import_file=True).create({"code":"550003", "name": "Existing Account"}).id

        result = self._create_save_import("account.account", self.coa_file_content)
        self.cr.precommit.run()
        self.env.company.account_opening_move_id.action_post()

        self.assertEqual(result["messages"], [], "The import should have been successful without error")

        existing_account = self.env["account.account"].browse(existing_id)
        self.assertEqual(len(result["ids"]), 14, "14 Accounts should have been imported")
        self.assertEqual(existing_account.name, "Bank", "The existing account should have been updated")
        self.assertEqual(existing_account.current_balance, -3500.0, "The balance should have been updated")

    @unittest.skipUnless(can_import("xlrd.xlsx"), "XLRD module not available")
    def test_account_move_line_xlsx_import(self):
        result = self._create_save_import("account.move.line", self.journal_items_file_content)

        account_move_lines = self.env["account.move.line"].browse(result["ids"])
        self.assertEqual(len(account_move_lines.mapped("move_id").ids), 4, "4 moves should have been created")
        self.assertEqual(account_move_lines.mapped("journal_id.code"), ["MISC", "SAL", "BNK1"], "The journals should be set correctly")
        self.assertEqual(account_move_lines.mapped("account_id.code"), ["700200", "400000", "455000", "620200"], "The accounts should be set correctly")
        account_move_lines.move_id.action_post()
        self.assertTrue(account_move_lines.full_reconcile_id)

    @unittest.skipUnless(can_import("xlrd.xlsx"), "XLRD module not available")
    def test_duplicate_journals_import(self):
        existing_journal = self.env["account.journal"].with_context(import_file=True).create({"name": "OD26_18"})
        self.assertEqual(existing_journal.code, 'OD26_')

        result = self._create_save_import("account.move.line", self.duplicate_journals_file_content)

        account_move_lines = self.env["account.move.line"].browse(result["ids"])
        self.assertEqual(len(account_move_lines.mapped("move_id").ids), 3, "3 moves should have been created")
        self.assertEqual(sorted(account_move_lines.mapped("journal_id.code")), ["GEN1", "OD26_", "OD_BL"], "The journals should be set correctly")
