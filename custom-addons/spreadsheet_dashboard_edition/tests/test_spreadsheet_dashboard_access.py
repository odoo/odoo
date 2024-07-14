import base64

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user


class SpreadsheetDashboardAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = cls.env["res.groups"].create({"name": "test group"})
        cls.user = new_test_user(cls.env, login="Raoul")
        cls.user.groups_id |= cls.group


    def test_join_new_dashboard_user(self):
        dashboard_group = self.env["spreadsheet.dashboard.group"].create({
            "name": "Dashboard group"
        })
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "spreadsheet_data": "{}",
                "group_ids": [Command.set(self.group.ids)],
                "dashboard_group_id": dashboard_group.id,
            }
        )
        # only read access, no one ever joined this dashboard
        result = dashboard.with_user(self.user).join_spreadsheet_session()
        self.assertEqual(result["data"], {})

    def test_update_data_reset_collaborative(self):
        dashboard_group = self.env["spreadsheet.dashboard.group"].create({
            "name": "Dashboard group"
        })
        dashboard = self.env["spreadsheet.dashboard"].create(
            {
                "name": "a dashboard",
                "spreadsheet_data": "{}",
                "group_ids": [Command.set(self.group.ids)],
                "dashboard_group_id": dashboard_group.id,
            }
        )
        dashboard.dispatch_spreadsheet_message({
            "type": "REMOTE_REVISION",
            "serverRevisionId": "rev-1-id",
            "nextRevisionId": "rev-2-id",
            "commands": [],
        })
        dashboard.dispatch_spreadsheet_message({
            "type": "SNAPSHOT",
            "serverRevisionId": "rev-2-id",
            "nextRevisionId": "rev-3-id",
            "data": {"revisionId": "rev-3-id"},
        })
        revisions = dashboard.with_context(active_test=False).spreadsheet_revision_ids
        self.assertEqual(len(revisions.exists()), 2)
        self.assertTrue(dashboard.spreadsheet_snapshot)
        dashboard.spreadsheet_data = "{ version: 2 }"
        self.assertFalse(revisions.exists())
        self.assertFalse(dashboard.spreadsheet_snapshot)
