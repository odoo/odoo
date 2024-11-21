import json

from odoo.exceptions import UserError

from .common import DashboardTestCommon


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

    def test_load_with_user_locale(self):
        dashboard = self.create_dashboard().with_user(self.user)
        self.user.lang = "en_US"
        data = dashboard.get_readonly_dashboard()
        locale = data["snapshot"]["settings"]["locale"]
        self.assertEqual(locale["code"], "en_US")
        self.assertEqual(len(data["revisions"]), 0)

        self.env.ref("base.lang_fr").active = True
        self.user.lang = "fr_FR"
        data = dashboard.get_readonly_dashboard()
        locale = data["snapshot"]["settings"]["locale"]
        self.assertEqual(locale["code"], "fr_FR")
        self.assertEqual(len(data["revisions"]), 0)

    def test_load_with_company_currency(self):
        dashboard = self.create_dashboard().with_user(self.user)
        data = dashboard.get_readonly_dashboard()
        self.assertEqual(
            data["default_currency"],
            self.env["res.currency"].get_company_currency_for_spreadsheet()
        )

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

    def test_get_sample_dashboard(self):
        sample_dashboard_path = "spreadsheet_dashboard/tests/data/sample_dashboard.json"
        dashboard = self.create_dashboard()
        dashboard.sample_dashboard_file_path = sample_dashboard_path
        dashboard.main_data_model_ids = [(4, self.env.ref("base.model_res_users").id)]
        self.env["res.users"].search([]).action_archive()

        self.assertEqual(dashboard.with_user(self.user).get_readonly_dashboard(), {
            "is_sample": True,
            "snapshot": {"sheets": []},
        })
