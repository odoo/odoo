from odoo.addons.spreadsheet.tests.validate_spreadsheet_data import (
    ValidateSpreadsheetData,
)
from odoo.tests.common import tagged


@tagged("-at_install", "post_install")
class TestSpreadsheetDashboardData(ValidateSpreadsheetData):
    def test_validate_dashboard_data(self):
        """validate fields and models used in dashboards"""
        dashboards = self.env["spreadsheet.dashboard"].search([])
        for dashboard in dashboards:
            with self.subTest(dashboard.name):
                self.validate_spreadsheet_data(dashboard.raw, dashboard.name)
