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
        self.assertEqual(dashboard.file_name, "My Dashboard.osheet.json")

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
