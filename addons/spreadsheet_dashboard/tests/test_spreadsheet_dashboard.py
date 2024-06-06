import base64
import json
from odoo.tests.common import TransactionCase, Form
from odoo.exceptions import UserError, ValidationError


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

    def test_copy_name(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "dashboard_group_id": group.id,
            }
        )
        copy = dashboard.copy()
        self.assertEqual(copy.name, "a dashboard (copy)")

        copy = dashboard.copy({"name": "a copy"})
        self.assertEqual(copy.name, "a copy")


    def test_write_raw_data(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "dashboard_group_id": group.id,
            }
        )
        data = b'{"version": 1, "sheets": [{"id": "sheet1", "name": "Sheet1"}]}'
        dashboard.raw = data
        self.assertEqual(dashboard.data, base64.encodebytes(data))

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

    def test_onchange_json_data(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        spreadsheet_form = Form(self.env['spreadsheet.dashboard'])
        spreadsheet_form.name = 'Test spreadsheet'
        spreadsheet_form.dashboard_group_id = group
        spreadsheet_form.data = base64.b64encode(json.dumps({'key': 'value'}).encode('utf-8'))
        with self.assertRaises(ValidationError, msg='Invalid JSON Data'):
            spreadsheet_form.data = base64.b64encode('invalid json'.encode('utf-8'))
