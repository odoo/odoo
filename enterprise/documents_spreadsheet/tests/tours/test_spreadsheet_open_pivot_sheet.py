# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ..common import SpreadsheetTestTourCommon

from odoo.tests import tagged

@tagged("post_install", "-at_install")
class TestSpreadsheetOpenPivot(SpreadsheetTestTourCommon):

    def test_01_spreadsheet_open_pivot_as_admin(self):
        self.start_tour("/odoo", "spreadsheet_open_pivot_sheet", login="admin")

    def test_01_spreadsheet_open_pivot_as_user(self):
        self.start_tour("/odoo", "spreadsheet_open_pivot_sheet", login="spreadsheetDude")
