from odoo.tests import tagged

from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged("post_install", "-at_install")
class TestMoOverviewReport(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref("mrp.mo_overview_section")
        cls.production = cls.env["mrp.production"].create(
            {
                "product_id": cls.product_4.id,
                "product_uom_id": cls.product_4.uom_id.id,
                "product_qty": 5.0,
                "bom_id": cls.bom_1.id,
            }
        )
        cls.production.action_confirm()

    def _options(self, **extra):
        return self.report.with_context(
            active_model="mrp.production", active_id=self.production.id
        ).get_options({"selected_variant_id": self.report.id, **extra})

    def _lines(self, options):
        return self.report._get_lines(options)

    def test_the_overview_opens_on_the_manufacturing_order_of_the_context(self):
        options = self._options()
        self.assertEqual(
            options["mo_overview_production_id"],
            self.production.id,
            "the client action passes the MO through the context",
        )
        lines = self._lines(options)
        self.assertEqual(lines[0]["name"], self.production.product_id.display_name)

    def test_every_component_of_the_data_layer_is_a_line(self):
        options = self._options()
        data = self.env["report.mrp.report_mo_overview"]._get_report_data(
            self.production.id
        )
        names = [line["name"] for line in self._lines(options)]
        for component in data["components"]:
            self.assertIn(component["summary"]["name"], names)

    def test_the_summary_line_carries_the_costs_of_the_data_layer(self):
        options = self._options()
        data = self.env["report.mrp.report_mo_overview"]._get_report_data(
            self.production.id
        )
        summary_line = self._lines(options)[0]
        values = {
            column["expression_label"]: cell.get("no_format")
            for column, cell in zip(
                options["columns"], summary_line["columns"], strict=True
            )
        }
        self.assertEqual(values["quantity"], data["summary"]["quantity"])
        self.assertEqual(values["mo_cost"], data["summary"]["mo_cost"])
        self.assertEqual(values["bom_cost"], data["summary"]["bom_cost"])

    def test_the_cost_columns_the_reader_switched_off_are_absent(self):
        options = self._options()
        labels = [column["expression_label"] for column in options["columns"]]
        self.assertIn("mo_cost", labels)
        self.assertNotIn("real_cost", labels, "real cost starts out hidden")

        mo_cost_column = self.env.ref("mrp.mo_overview_report_column_mo_cost")
        options = self._options(hidden_columns=[mo_cost_column.id])
        self.assertNotIn(
            "mo_cost", [column["expression_label"] for column in options["columns"]]
        )
        self.assertTrue(
            all(
                len(line["columns"]) == len(options["columns"])
                for line in self._lines(options)
            )
        )

    def test_the_total_lines_state_the_unit_cost(self):
        options = self._options()
        data = self.env["report.mrp.report_mo_overview"]._get_report_data(
            self.production.id
        )
        total_lines = [
            line for line in self._lines(options) if line.get("class") == "total"
        ]
        self.assertEqual([line["name"] for line in total_lines], ["Unit Cost"])
        values = {
            column["expression_label"]: cell.get("no_format")
            for column, cell in zip(
                options["columns"], total_lines[0]["columns"], strict=True
            )
        }
        self.assertEqual(values["mo_cost"], data["extras"]["unit_mo_cost"])

    def test_the_overview_is_one_section_of_the_manufacturing_report(self):
        root = self.env.ref("mrp.mo_overview_report")
        self.assertEqual(
            root.section_report_ids,
            self.report + self.env.ref("mrp.mo_cost_breakdown_section"),
        )
        options = root.with_context(
            active_model="mrp.production", active_id=self.production.id
        ).get_options({"selected_variant_id": root.id})
        self.assertEqual(
            [section["name"] for section in options["sections"]],
            ["Overview", "Cost Breakdown"],
        )

    def test_the_cost_breakdown_section_mirrors_the_data_layer(self):
        breakdown = self.env.ref("mrp.mo_cost_breakdown_section")
        options = breakdown.with_context(
            active_model="mrp.production", active_id=self.production.id
        ).get_options({"selected_variant_id": breakdown.id})
        data = self.env["report.mrp.report_mo_overview"]._get_report_data(
            self.production.id
        )
        self.assertEqual(
            [line["name"] for line in breakdown._get_lines(options)],
            [row["name"] for row in data["cost_breakdown"]],
        )
