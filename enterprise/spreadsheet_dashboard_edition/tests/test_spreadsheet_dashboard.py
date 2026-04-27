import json
from odoo.tools import file_open
from odoo.addons.spreadsheet_dashboard.tests.common import DashboardTestCommon
from odoo.addons.spreadsheet_edition.tests.spreadsheet_test_case import SpreadsheetTestCase


class TestSpreadsheetDashboard(DashboardTestCommon, SpreadsheetTestCase):
    def test_computed_name(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "My Dashboard",
                "dashboard_group_id": group.id,
                "spreadsheet_data": "{}",
            }
        )
        self.assertEqual(dashboard.spreadsheet_file_name, "My Dashboard.osheet.json")

    def test_join_published(self):
        dashboard = self.create_dashboard().with_user(self.user)
        self.assertTrue(dashboard.join_spreadsheet_session()["is_published"])
        dashboard.sudo().is_published = False
        self.assertFalse(dashboard.join_spreadsheet_session()["is_published"])

    def test_load_with_user_locale(self):
        dashboard = self.create_dashboard().with_user(self.user)

        self.user.lang = "en_US"
        data = dashboard.get_readonly_dashboard()
        snapshot = data["snapshot"]
        snapshot_locale = snapshot["settings"]["locale"]
        self.assertEqual(snapshot_locale["code"], "en_US")
        revisions = data["revisions"]
        self.assertEqual(len(revisions), 1)
        locale_revision = revisions[-1]
        self.assertEqual(locale_revision["serverRevisionId"], snapshot["revisionId"])
        self.assertEqual(locale_revision["commands"][0]["type"], "UPDATE_LOCALE")
        self.assertEqual(locale_revision["commands"][0]["locale"]["code"], "en_US")
        self.assertEqual(locale_revision["commands"][0]["locale"]["weekStart"], 7)

        self.env.ref("base.lang_fr").active = True
        self.user.lang = "fr_FR"

        data = dashboard.get_readonly_dashboard()
        snapshot = data["snapshot"]
        snapshot_locale = snapshot["settings"]["locale"]
        self.assertEqual(
            snapshot_locale["code"], "en_US", "snapshot locale is not changed"
        )
        revisions = data["revisions"]
        locale_revision = revisions[-1]
        self.assertEqual(locale_revision["serverRevisionId"], snapshot["revisionId"])
        self.assertEqual(locale_revision["commands"][0]["type"], "UPDATE_LOCALE")
        self.assertEqual(locale_revision["commands"][0]["locale"]["code"], "fr_FR")
        self.assertEqual(locale_revision["commands"][0]["locale"]["weekStart"], 1)

    def test_load_with_company_currency(self):
        dashboard = self.create_dashboard().with_user(self.user)
        data = dashboard.get_readonly_dashboard()
        self.assertEqual(
            data["default_currency"],
            self.env["res.currency"].get_company_currency_for_spreadsheet()
        )

    def test_load_with_user_locale_existing_revisions(self):
        dashboard = self.create_dashboard()
        dashboard.dispatch_spreadsheet_message(self.new_revision_data(dashboard))

        data = dashboard.with_user(self.user).get_readonly_dashboard()
        revisions = data["revisions"]
        self.assertEqual(len(revisions), 2)
        self.assertEqual(
            revisions[-1]["serverRevisionId"],
            revisions[-2]["nextRevisionId"],
            "revisions ids are chained",
        )

    def test_load_sample_dashboard(self):
        sample_dashboard_path = "spreadsheet_dashboard_edition/tests/data/sample_dashboard.json"

        def get_sample_data():
            with file_open(sample_dashboard_path, 'rb') as f:
                return json.load(f)
        dashboard = self.create_dashboard()
        dashboard.main_data_model_ids = [(4, self.env.ref("base.model_res_users").id)]
        dashboard.sample_dashboard_file_path = sample_dashboard_path

        # when no records are available for the main data model and no revisions, the sample data is loaded
        self.env["res.users"].search([]).action_archive()
        self.env["spreadsheet.revision"].search([]).unlink()
        data = dashboard.get_readonly_dashboard()
        self.assertTrue(data["is_sample"])
        self.assertEqual(data["snapshot"], get_sample_data())

        # when there are revisions, the sample data is not loaded
        dashboard.dispatch_spreadsheet_message(self.new_revision_data(dashboard))
        data = dashboard.get_readonly_dashboard()
        self.assertFalse(data.get("is_sample"))
        self.assertNotEqual(data["snapshot"], get_sample_data())

        # when no revisions, but we have records for the main data model, the sample data is not loaded
        self.env["spreadsheet.revision"].search([]).unlink()
        self.env["res.users"].create({"login": "new_user", "name": "New User"})
        data = dashboard.get_readonly_dashboard()
        self.assertFalse(data.get("is_sample"))
        self.assertNotEqual(data["snapshot"], get_sample_data())

    def test_get_selector_spreadsheet_models(self):
        result = self.env["spreadsheet.mixin"].with_user(self.user).get_selector_spreadsheet_models()
        self.assertFalse(any(r["model"] == "spreadsheet.dashboard" for r in result))

        self.user.groups_id |= self.env.ref("spreadsheet_dashboard.group_dashboard_manager")
        result = self.env["spreadsheet.mixin"].with_user(self.user).get_selector_spreadsheet_models()
        self.assertTrue(any(r["model"] == "spreadsheet.dashboard" for r in result))
