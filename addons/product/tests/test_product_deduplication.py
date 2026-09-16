from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import ProductCommon, ProductVariantsCommon


@tagged("post_install", "-at_install")
class TestSharedPricing(ProductVariantsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env["product.template"].create(
            {
                "name": "Priced Widget",
                "uom_id": cls.uom_unit.id,
                "list_price": 100.0,
            }
        )
        cls.variant = cls.template.product_variant_id
        cls.variant.standard_price = 40.0

    def test_both_models_answer_the_same_price(self):
        for price_type, expected in (("list_price", 100.0), ("standard_price", 40.0)):
            with self.subTest(price_type=price_type):
                self.assertEqual(
                    self.template._get_prices(price_type)[self.template.id],
                    expected,
                )
                self.assertEqual(
                    self.variant._get_prices(price_type)[self.variant.id],
                    expected,
                )

    def test_both_models_convert_the_unit_the_same_way(self):
        self.assertEqual(
            self.template._get_prices("list_price", uom=self.uom_dozen)[
                self.template.id
            ],
            self.variant._get_prices("list_price", uom=self.uom_dozen)[self.variant.id],
        )

    def test_both_models_refuse_an_incompatible_unit(self):
        for record in (self.template, self.variant):
            with self.subTest(model=record._name), self.assertRaises(UserError):
                record._get_prices("list_price", uom=self.uom_kgm)

    def test_the_template_still_falls_back_to_its_first_variant_cost(self):
        multi = self.product_template_sofa
        self.assertGreater(len(multi.product_variant_ids), 1)
        multi.product_variant_ids.standard_price = 0.0
        multi.product_variant_ids[0].standard_price = 33.0

        self.assertEqual(multi._get_prices("standard_price")[multi.id], 33.0)
        second = multi.product_variant_ids[1]
        self.assertEqual(second._get_prices("standard_price")[second.id], 0.0)

    def test_the_hooks_are_what_a_subclass_overrides(self):
        mixin = self.env["mixin.product.price"]
        for hook in ("_get_price_base", "_get_price_currency"):
            self.assertTrue(hasattr(mixin, hook), hook)
        self.assertEqual(
            self.variant._get_price_currency("standard_price"),
            self.variant.cost_currency_id,
        )
        self.assertEqual(
            self.variant._get_price_currency("list_price"), self.variant.currency_id
        )


@tagged("post_install", "-at_install")
class TestLabelReportIsShared(ProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product.barcode = "LBL-1"
        cls.layout = cls.env["product.label.layout"].create(
            {
                "product_tmpl_ids": [Command.set(cls.product.product_tmpl_id.ids)],
                "custom_quantity": 3,
            }
        )

    FORMATS = (
        "report.product.report_producttemplatelabel2x7",
        "report.product.report_producttemplatelabel4x7",
        "report.product.report_producttemplatelabel4x12",
        "report.product.report_producttemplatelabel4x12noprice",
        "report.product.report_producttemplatelabel_dymo",
    )

    def _data(self, **overrides):
        return {
            "active_model": "product.template",
            "layout_wizard": self.layout.id,
            "quantity_by_product": {self.product.product_tmpl_id.id: 3},
            **overrides,
        }

    def test_every_format_inherits_the_shared_pipeline(self):
        for name in self.FORMATS:
            with self.subTest(report=name):
                report = self.env[name]
                self.assertIn("mixin.product.label.report", report._inherit_module)
                values = report._get_report_values([], self._data())
                self.assertEqual(values["page_numbers"], 1)
                self.assertEqual(list(values["quantity"].values()), [[("LBL-1", 3)]])

    def test_ids_survive_a_json_round_trip(self):
        values = self.env[self.FORMATS[0]]._get_report_values(
            [],
            self._data(
                layout_wizard=str(self.layout.id),
                quantity_by_product={str(self.product.product_tmpl_id.id): "3"},
            ),
        )
        self.assertEqual(list(values["quantity"].values()), [[("LBL-1", 3)]])

    def test_client_supplied_junk_is_a_user_error(self):
        report = self.env[self.FORMATS[0]]
        for label, data in (
            ("non-numeric product id", self._data(quantity_by_product={"abc": 3})),
            (
                "non-numeric quantity",
                self._data(
                    quantity_by_product={self.product.product_tmpl_id.id: "many"}
                ),
            ),
            ("non-numeric layout id", self._data(layout_wizard="xyz")),
            ("nothing to print", self._data(quantity_by_product={})),
            (
                "zero labels",
                self._data(quantity_by_product={self.product.product_tmpl_id.id: 0}),
            ),
            ("unknown model", self._data(active_model="res.partner")),
        ):
            with self.subTest(case=label), self.assertRaises(UserError):
                report._get_report_values([], data)

    def test_a_deleted_product_in_custom_barcodes_is_skipped(self):
        values = self.env[self.FORMATS[0]]._get_report_values(
            [], self._data(custom_barcodes={"999999999": [("Z", 1)]})
        )
        self.assertEqual(list(values["quantity"].values()), [[("LBL-1", 3)]])


@tagged("post_install", "-at_install")
class TestImportContinuationRows(ProductCommon):
    def test_a_second_vendor_line_stays_with_its_product(self):
        vendors = self.env["res.partner"].create(
            [{"name": "Cont Vendor A"}, {"name": "Cont Vendor B"}]
        )
        result = (
            self.env["product.template"]
            .with_context(import_file=True)
            .load(
                [
                    "name",
                    "import_attribute_values",
                    "seller_ids/partner_id",
                    "seller_ids/price",
                ],
                [
                    ["Cont Shirt", "ContColor:Red", vendors[0].name, "10"],
                    ["", "", vendors[1].name, "12"],
                    ["Cont Mug", "ContColor:Blue", vendors[0].name, "7"],
                ],
            )
        )
        self.assertFalse(
            [m for m in result["messages"] if m["type"] == "error"], result["messages"]
        )
        shirt = self.env["product.template"].search([("name", "=", "Cont Shirt")])
        self.assertEqual(
            sorted(shirt.seller_ids.mapped("price")),
            [10.0, 12.0],
            "both vendor lines belong to the shirt",
        )
        self.assertEqual(
            shirt.product_variant_ids.product_template_attribute_value_ids.mapped(
                "name"
            ),
            ["Red"],
        )
        mug = self.env["product.template"].search([("name", "=", "Cont Mug")])
        self.assertEqual(mug.seller_ids.mapped("price"), [7.0])

    def test_a_continuation_row_follows_a_plain_template_row_too(self):
        vendors = self.env["res.partner"].create(
            [{"name": "Plain Vendor A"}, {"name": "Plain Vendor B"}]
        )
        result = (
            self.env["product.template"]
            .with_context(import_file=True)
            .load(
                [
                    "name",
                    "import_attribute_values",
                    "seller_ids/partner_id",
                    "seller_ids/price",
                ],
                [
                    ["Plain Widget", "", vendors[0].name, "3"],
                    ["", "", vendors[1].name, "4"],
                ],
            )
        )
        self.assertFalse(
            [m for m in result["messages"] if m["type"] == "error"], result["messages"]
        )
        widget = self.env["product.template"].search([("name", "=", "Plain Widget")])
        self.assertEqual(sorted(widget.seller_ids.mapped("price")), [3.0, 4.0])

    def test_a_file_with_no_one2many_column_is_unaffected(self):
        rows = [["NoO2M A", ""], ["NoO2M B", "NoO2MColor:Red"]]
        flags = self.env["product.template"]._import_continuation_rows(
            ["name", "import_attribute_values"], rows
        )
        self.assertEqual(flags, [False, False])
