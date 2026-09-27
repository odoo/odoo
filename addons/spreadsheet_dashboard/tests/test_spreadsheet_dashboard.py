import json

from odoo import Command
from odoo.exceptions import UserError

from odoo.tests import tagged

from .common import DashboardTestCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSpreadsheetDashboard(DashboardTestCommon):
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

    def test_copy_group_name(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "My section"}
        )

        copy = group.copy()
        self.assertEqual(copy.name, "My section (copy)")

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

    def test_unpublish_dashboard(self):
        group = self.env["spreadsheet.dashboard.group"].create({
            "name": "Dashboard group"
        })
        dashboard = self.create_dashboard(group)
        self.assertEqual(group.published_dashboard_ids, dashboard)
        dashboard.is_published = False
        self.assertFalse(group.published_dashboard_ids)

    def test_publish_dashboard(self):
        group = self.env["spreadsheet.dashboard.group"].create({
            "name": "Dashboard group"
        })
        dashboard = self.create_dashboard(group)
        dashboard.is_published = False
        self.assertFalse(group.published_dashboard_ids)
        dashboard.is_published = True
        self.assertEqual(group.published_dashboard_ids, dashboard)

    def test_toggle_favorite(self):
        dashboard = self.create_dashboard().with_user(self.user)

        self.assertFalse(dashboard.is_favorite)
        self.assertNotIn(self.user, dashboard.favorite_user_ids)

        dashboard.with_user(self.user).action_toggle_favorite()

        self.assertTrue(dashboard.is_favorite)
        self.assertIn(self.user, dashboard.favorite_user_ids)

        dashboard.with_user(self.user).action_toggle_favorite()

        self.assertFalse(dashboard.is_favorite)
        self.assertNotIn(self.user, dashboard.favorite_user_ids)

    def test_allowed_user_ids_grants_access(self):
        group = self.env["spreadsheet.dashboard.group"].create({"name": "a group"})
        dashboard = self.env["spreadsheet.dashboard"].create({
            "name": "user-restricted dashboard",
            "dashboard_group_id": group.id,
            "group_ids": [],
            "allowed_user_ids": [Command.link(self.user.id)],
        })
        result = self.env["spreadsheet.dashboard"].with_user(self.user).search([("id", "=", dashboard.id)])
        self.assertEqual(result, dashboard)

    def test_user_not_in_allowed_user_ids_cannot_access(self):
        group = self.env["spreadsheet.dashboard.group"].create({"name": "a group"})
        dashboard = self.env["spreadsheet.dashboard"].create({
            "name": "private dashboard",
            "dashboard_group_id": group.id,
            "group_ids": [],
            "allowed_user_ids": [],
        })
        result = self.env["spreadsheet.dashboard"].with_user(self.user).search([("id", "=", dashboard.id)])
        self.assertFalse(result)
