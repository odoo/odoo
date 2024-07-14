# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo.tools import file_open


@tagged("post_install", "-at_install")
class TestSpreadsheetImportXLSXUi(HttpCase):
    def test_01_spreadsheet_clone_and_archive_xlsx(self):
        with file_open('documents_spreadsheet/tests/data/test.xlsx', 'rb') as f:
            spreadsheet_data = base64.encodebytes(f.read())

        folder = self.env["documents.folder"].create({"name": "Test folder"})
        self.env['documents.document'].create({
            'datas': spreadsheet_data,
            'name': 'test.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'folder_id': folder.id
        })

        self.start_tour("/web", "spreadsheet_clone_xlsx", login="admin")
