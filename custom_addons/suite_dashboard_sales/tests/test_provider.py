from odoo.tests import common


class TestSuiteDashboardSalesProvider(common.TransactionCase):
    def test_sales_workspace_payload(self):
        template = self.env.ref("suite_dashboard_sales.suite_dashboard_template_sales_command_center")
        workspace = self.env["suite.dashboard.workspace"].create(
            {
                "name": "Sales Test",
                "provider_key": "sales",
                "template_id": template.id,
            }
        )

        payload = workspace.get_dashboard_payload({"date_filter": "mtd"})

        self.assertEqual(payload["workspace"]["provider_key"], "sales")
        self.assertTrue(payload["widgets"])
        self.assertTrue(any(widget["widget_key"] == "sale_booked_revenue" for widget in payload["widgets"]))
        self.assertTrue(any(widget["widget_key"] == "sale_revenue_trend" for widget in payload["widgets"]))
        self.assertTrue(any(widget["widget_key"] == "sale_top_customers" for widget in payload["widgets"]))
        self.assertTrue(payload["hero_metrics"])
        self.assertTrue(payload["quick_access"])
