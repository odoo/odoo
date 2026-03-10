from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import common


class TestSuiteDashboardCore(common.TransactionCase):
    def test_workspace_copies_template_items(self):
        template = self.env["suite.dashboard.template"].create(
            {
                "name": "Ops Command",
                "code": "ops_command",
                "provider_key": "missing",
                "default_filter_state": '{"date_filter":"ytd"}',
                "item_definition_json": '[{"widget_key":"ops_kpi","col_span":3,"row_span":1}]',
            }
        )
        workspace = self.env["suite.dashboard.workspace"].create(
            {
                "template_id": template.id,
                "provider_key": template.provider_key,
            }
        )

        self.assertEqual(workspace.filter_state, '{"date_filter":"ytd"}')
        self.assertEqual(workspace.item_ids.widget_key, "ops_kpi")
        self.assertEqual(workspace.item_ids.col_span, 3)

    def test_missing_provider_raises_user_error(self):
        workspace = self.env["suite.dashboard.workspace"].create(
            {
                "name": "Missing Provider",
                "provider_key": "missing",
            }
        )
        with self.assertRaises(UserError):
            workspace.get_dashboard_payload({"date_filter": "mtd"})

    def test_toggle_favorite_updates_membership(self):
        user = self.env.ref("base.user_admin")
        user.write(
            {
                "group_ids": [
                    Command.link(self.env.ref("suite_dashboard_core.group_suite_dashboard_user").id)
                ]
            }
        )
        workspace = self.env["suite.dashboard.workspace"].with_user(user).create(
            {
                "name": "Favorite Workspace",
                "provider_key": "missing",
            }
        )
        workspace.favorite_user_ids = [Command.clear()]
        workspace.action_toggle_favorite()
        self.assertIn(user, workspace.favorite_user_ids)
        self.assertTrue(workspace.is_favorite)
