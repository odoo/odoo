from odoo.tests import common


class TestSuiteDashboardHrProvider(common.TransactionCase):
    def test_hr_workspace_payload(self):
        template = self.env.ref("suite_dashboard_hr.suite_dashboard_template_people_command_center")
        workspace = self.env["suite.dashboard.workspace"].create(
            {
                "name": "People Test",
                "provider_key": "hr",
                "template_id": template.id,
            }
        )

        payload = workspace.get_dashboard_payload({"date_filter": "today"})

        self.assertEqual(payload["workspace"]["provider_key"], "hr")
        self.assertTrue(payload["widgets"])
        self.assertTrue(any(widget["widget_key"] == "hr_headcount" for widget in payload["widgets"]))
        self.assertTrue(any(widget["widget_key"] == "hr_dept_breakdown" for widget in payload["widgets"]))
        self.assertEqual(
            any(widget["widget_key"] == "hr_leaves_pending" for widget in payload["widgets"]),
            bool(self.env.registry.get("hr.leave")),
        )
        self.assertTrue(payload["hero_metrics"])
        self.assertTrue(payload["quick_access"])
