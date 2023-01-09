from odoo.tests.common import TransactionCase


class TestSpreadsheetDashboard(TransactionCase):
    def test_create_with_default_values(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "dashboard_group_id": group.id,
            }
        )
        self.assertEqual(dashboard.group_ids, self.env.ref("base.group_user"))
        self.assertEqual(
            dashboard.raw,
            b'{"version": 1, "sheets": [{"id": "sheet1", "name": "Sheet1"}]}',
        )
