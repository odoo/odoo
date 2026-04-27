# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from ..common import SpreadsheetTestTourCommon


@tagged("post_install", "-at_install")
class TestSpreadsheetCreateEmpty(SpreadsheetTestTourCommon):
    def test_01_spreadsheet_create_empty(self):
        self.start_tour("/odoo", "spreadsheet_create_empty_sheet", login="admin")

    def test_02_spreadsheet_create_list_view(self):
        self.start_tour("/odoo", "spreadsheet_create_list_view", login="admin")
