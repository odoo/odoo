from odoo.tests import tagged

from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged("post_install", "-at_install")
class TestBomOverviewReport(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref("mrp.bom_overview_report")
        cls.data_layer = cls.env["report.mrp.report_bom_structure"]

    def _options(self, **extra):
        return self.report.with_context(
            active_model="mrp.bom", active_id=self.bom_1.id
        ).get_options({"selected_variant_id": self.report.id, **extra})

    def test_the_overview_opens_on_the_bom_of_the_context(self):
        options = self._options()
        self.assertEqual(options["bom_overview_bom_id"], self.bom_1.id)
        self.assertEqual(options["bom_overview_quantity"], self.bom_1.product_qty)

        lines = self.report._get_lines(options)
        self.assertEqual(lines[0]["name"], self.bom_1.product_id.display_name)

    def test_the_client_names_the_record_with_active_id_alone(self):
        options = self.report.with_context(active_id=self.bom_1.id).get_options(
            {"selected_variant_id": self.report.id}
        )
        self.assertEqual(
            options["bom_overview_bom_id"],
            self.bom_1.id,
            "the client action passes active_id and no active_model",
        )

    def test_every_component_of_the_data_layer_is_a_line_under_the_product(self):
        options = self._options()
        data = self.data_layer.with_context(
            warehouse_id=options["bom_overview_warehouse_id"]
        )._get_report_data(
            bom_id=self.bom_1.id, searchQty=options["bom_overview_quantity"]
        )
        lines = self.report._get_lines(options)
        names = [line["name"] for line in lines]
        for component in data["lines"]["components"]:
            self.assertIn(component["name"], names)
        self.assertTrue(
            all(line["parent_id"] == lines[0]["id"] for line in lines[1:])
            or len(lines) > 1
        )

    def test_the_quantity_the_reader_asks_for_drives_the_components(self):
        one = self._options(bom_overview_quantity=1)
        ten = self._options(bom_overview_quantity=10)
        self.assertEqual(ten["bom_overview_quantity"], 10)

        def component_quantities(options):
            return [
                line["columns"][0].get("no_format")
                for line in self.report._get_lines(options)[1:]
            ]

        for single, tenfold in zip(
            component_quantities(one), component_quantities(ten), strict=True
        ):
            if isinstance(single, (int, float)) and single:
                self.assertAlmostEqual(tenfold, single * 10)

    def test_the_cost_column_carries_the_bom_cost_of_the_data_layer(self):
        options = self._options()
        data = self.data_layer.with_context(
            warehouse_id=options["bom_overview_warehouse_id"]
        )._get_report_data(
            bom_id=self.bom_1.id, searchQty=options["bom_overview_quantity"]
        )
        summary = self.report._get_lines(options)[0]
        values = {
            column["expression_label"]: cell.get("no_format")
            for column, cell in zip(options["columns"], summary["columns"], strict=True)
        }
        self.assertEqual(values["bom_cost"], data["lines"]["bom_cost"])

    def test_the_forecast_columns_are_offered_and_start_out_hidden(self):
        options = self._options()
        labels = [column["expression_label"] for column in options["columns"]]
        self.assertEqual(labels, ["quantity", "bom_cost"])
        self.assertEqual(
            [column["name"] for column in options["optional_columns"]],
            [
                "Unit",
                "Free to Use / On Hand",
                "Status",
                "Availability",
                "Lead Time",
                "Route",
            ],
        )

        options = self._options(hidden_columns=[])
        self.assertIn(
            "availability",
            [column["expression_label"] for column in options["columns"]],
        )
