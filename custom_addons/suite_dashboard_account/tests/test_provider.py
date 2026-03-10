from odoo.tests import common


class TestSuiteDashboardAccountProvider(common.TransactionCase):
    def test_account_workspace_payload(self):
        template = self.env.ref(
            "suite_dashboard_account.suite_dashboard_template_finance_control_tower"
        )
        workspace = self.env["suite.dashboard.workspace"].create(
            {
                "name": "Finance Test",
                "provider_key": "account",
                "template_id": template.id,
            }
        )

        payload = workspace.get_dashboard_payload({"date_filter": "mtd"})

        self.assertEqual(payload["workspace"]["provider_key"], "account")
        self.assertTrue(payload["widgets"])
        self.assertTrue(
            any(widget["widget_key"] == "acc_revenue_mtd" for widget in payload["widgets"])
        )
        self.assertTrue(
            any(widget["widget_key"] == "acc_liquidity_pulse" for widget in payload["widgets"])
        )
        self.assertTrue(payload["hero_metrics"])
        self.assertTrue(payload["quick_access"])
