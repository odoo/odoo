# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch


from odoo.tests.common import HttpCase, new_test_user
from odoo.addons.spreadsheet_edition.tests.spreadsheet_test_case import SpreadsheetTestCase
from odoo.tools import file_open, misc


TEST_CONTENT = "{}"
GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


class SpreadsheetTestCommon(SpreadsheetTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder = cls.env["documents.document"].create({
            "name": "Test folder",
            "type": "folder",
            "access_internal": "view",
            "access_via_link": "none",
            "owner_id": cls.env.ref('base.user_root').id,
            "folder_id": False,
        })
        cls.spreadsheet_user = new_test_user(
            cls.env, login="spreadsheetDude", groups="documents.group_documents_user"
        )

    def create_spreadsheet(self, values=None, *, user=None, name="Untitled Spreadsheet"):
        def _create():
            vals = {
                "spreadsheet_data": r"{}",
                "folder_id": self.folder.id,
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
                "name": name,
                "access_via_link": "view",
                **(values or {}),
            }
            return self.env["documents.document"].with_user(user or self.env.user).create(vals)

        if values and 'create_date' in values:
            _create = patch.object(self.env.cr, 'now', lambda: values['create_date'])(_create)

        return _create()

    @contextmanager
    def _freeze_time(self, time):
        time_format = "%Y-%m-%d %H:%M" if ':' in time else "%Y-%m-%d"
        with patch.object(self.env.cr, 'now', lambda: datetime.strptime(time, time_format)), freeze_time(time):
            yield


class SpreadsheetTestTourCommon(SpreadsheetTestCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spreadsheet_user.partner_id.country_id = cls.env.ref("base.us")
        cls.env['res.users'].browse(2).partner_id.country_id = cls.env.ref("base.be")
        # Avoid interference from the demo data which rename the admin user
        cls.env['res.users'].browse(2).write({"name": "AdminDude"})
        data_path = misc.file_path('documents_spreadsheet/tests/test_spreadsheet_data.json')
        with file_open(data_path, 'rb') as f:
            cls.spreadsheet = cls.env["documents.document"].create({
                "handler": "spreadsheet",
                "folder_id": cls.folder.id,
                "raw": f.read(),
                "name": "Res Partner Test Spreadsheet",
                "access_internal": "edit",
            })
