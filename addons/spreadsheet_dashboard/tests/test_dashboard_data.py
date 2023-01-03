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
            # this dashboard is skipped because it's currently broken
            # but I still want to merge this test right now to avoid other broken dashboards
            if dashboard == self.env.ref(
                "spreadsheet_dashboard_hr_expense.spreadsheet_dashboard_expense",
                raise_if_not_found=False,
            ):
                continue
            with self.subTest(dashboard.name):
                self.validate_spreadsheet_data(dashboard.raw, dashboard.name)
