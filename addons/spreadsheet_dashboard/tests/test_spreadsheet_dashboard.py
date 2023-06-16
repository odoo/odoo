import json

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

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
            json.loads(dashboard.spreadsheet_data),
            dashboard._empty_spreadsheet_data()
        )

    def test_unlink_prevent_spreadsheet_group(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a_group"}
        )
        self.env['ir.model.data'].create({
            'name': group.name,
            'module': 'spreadsheet_dashboard',
            'model': group._name,
            'res_id': group.id,
        })
        with self.assertRaises(UserError, msg="You cannot delete a_group as it is used in another module"):
            group.unlink()
