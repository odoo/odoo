from odoo import fields
from odoo.tests import tagged

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged("post_install", "-at_install")
class TestStockValuationReport(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref("stock_account.stock_valuation_report")

    def _receive_ship_and_lose(self):
        # 10 in at 10, 3 shipped, 1 lost to the inventory location
        inventory_account = self._use_inventory_location_accounting()
        product = self.product_avco.with_company(self.company)
        self._make_in_move(product, 10, unit_cost=10)
        self._make_out_move(product, 3)
        self._make_out_move(product, 1, location_dest_id=self.inventory_location.id)
        return inventory_account

    def _lines(self, date=None):
        date = fields.Date.to_string(date or fields.Date.context_today(self.report))
        report = self.report.with_company(self.company)
        options = report.get_options(
            {
                "selected_variant_id": self.report.id,
                "date": {"date_to": date, "mode": "single", "filter": "custom"},
            }
        )
        return {
            line["name"]: {
                column["expression_label"]: column["no_format"]
                for column in line["columns"]
            }
            for line in report._get_lines(options)
        }

    def test_the_sections_carry_the_valuation_by_account(self):
        inventory_account = self._receive_ship_and_lose()
        stock = self.account_stock_valuation
        variation = self.account_stock_variation
        lines = self._lines()

        self.assertEqual(lines["Initial Balance"]["value"], 0)
        self.assertEqual(lines["Inventory Loss"]["value"], -10)
        self.assertEqual(lines["Stock Variation"]["value"], 70)
        self.assertEqual(lines["Ending Stock"]["value"], 60)
        self.assertEqual(lines[stock.display_name]["value"], 60)
        self.assertEqual(
            (
                lines[inventory_account.display_name]["debit"],
                lines[variation.display_name]["credit"],
            ),
            (10, 70),
        )

    def test_the_report_reads_the_same_figures_as_the_valuation_data(self):
        self._receive_ship_and_lose()
        data = (
            self.env["stock_account.stock.valuation.report"]
            .with_company(self.company)
            .with_context(allowed_company_ids=self.company.ids)
            ._get_report_data()
        )
        lines = self._lines()
        for section, name in (
            ("initial_balance", "Initial Balance"),
            ("inventory_loss", "Inventory Loss"),
            ("stock_variation", "Stock Variation"),
            ("ending_stock", "Ending Stock"),
        ):
            self.assertEqual(lines[name]["value"], data[section]["value"], section)

    def test_a_section_click_carries_the_report_date(self):
        self._receive_ship_and_lose()
        yesterday = fields.Date.subtract(fields.Date.context_today(self.report), days=1)
        report = self.report.with_company(self.company)
        options = report.get_options(
            {
                "selected_variant_id": self.report.id,
                "date": {
                    "date_to": fields.Date.to_string(yesterday),
                    "mode": "single",
                    "filter": "custom",
                },
            }
        )
        loss = self.env.ref("stock_account.stock_valuation_report_line_inventory_loss")
        action = report.dispatch_report_action(
            options,
            "execute_action",
            {
                "actionId": loss.action_id.id,
                "id": report._get_generic_line_id("account.report.line", loss.id),
            },
        )
        self.assertEqual(action["res_model"], "stock.move")
        self.assertIn(
            ("date", "<=", fields.Date.to_string(yesterday)), action["domain"]
        )
        self.assertIn(("location_id.usage", "=", "inventory"), action["domain"])

    def test_generate_entry_is_a_button_of_the_report(self):
        options = self.report.with_company(self.company).get_options(
            {"selected_variant_id": self.report.id}
        )
        self.assertIn(
            "action_generate_entry",
            [button["action"] for button in options["buttons"]],
        )
