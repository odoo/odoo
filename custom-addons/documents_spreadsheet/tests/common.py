# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, new_test_user
from odoo.addons.spreadsheet_edition.tests.spreadsheet_test_case import SpreadsheetTestCase
from odoo.tools import file_open, misc

from uuid import uuid4

TEST_CONTENT = "{}"
GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


class SpreadsheetTestCommon(SpreadsheetTestCase):
    @classmethod
    def setUpClass(cls):
        super(SpreadsheetTestCommon, cls).setUpClass()
        cls.folder = cls.env["documents.folder"].create({"name": "Test folder"})
        cls.spreadsheet_user = new_test_user(
            cls.env, login="spreadsheetDude", groups="documents.group_documents_user"
        )

    def create_spreadsheet(self, values=None, *, user=None, name="Untitled Spreadsheet"):
        if values is None:
            values = {}
        return (
            self.env["documents.document"]
            .with_user(user or self.env.user)
            .create({
                "spreadsheet_data": r"{}",
                "folder_id": self.folder.id,
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
                "name": name,
                **values,
            })
        )

    def share_spreadsheet(self, document):
        share = self.env["documents.share"].create(
            {
                "folder_id": document.folder_id.id,
                "document_ids": [(6, 0, [document.id])],
                "type": "ids",
            }
        )
        self.env["documents.shared.spreadsheet"].create(
            {
                "share_id": share.id,
                "document_id": document.id,
                "spreadsheet_data": document.spreadsheet_data,
            }
        )
        return share


class SpreadsheetTestTourCommon(SpreadsheetTestCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super(SpreadsheetTestTourCommon, cls).setUpClass()
        cls.spreadsheet_user.partner_id.country_id = cls.env.ref("base.us")
        cls.env['res.users'].browse(2).partner_id.country_id = cls.env.ref("base.be")
        # Avoid interference from the demo data which rename the admin user
        cls.env['res.users'].browse(2).write({"name": "AdminDude"})
        data_path = misc.file_path('documents_spreadsheet/demo/files/res_partner_spreadsheet.json')
        with file_open(data_path, 'rb') as f:
            cls.spreadsheet = cls.env["documents.document"].create({
                "handler": "spreadsheet",
                "folder_id": cls.folder.id,
                "raw": f.read(),
                "name": "Res Partner Test Spreadsheet"
            })
