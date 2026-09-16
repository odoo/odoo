from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductCommon


@tagged("post_install", "-at_install")
class TestAttributeLineCreateOrder(ProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attr_color = cls.env["product.attribute"].create(
            {
                "name": "OrderColor",
                "create_variant": "always",
                "value_ids": [Command.create({"name": "OrderRed"})],
            }
        )
        cls.attr_size = cls.env["product.attribute"].create(
            {
                "name": "OrderSize",
                "create_variant": "always",
                "value_ids": [Command.create({"name": "OrderBig"})],
            }
        )

    def _archived_line(self, template, attribute):
        line = self.env["product.template.attribute.line"].create(
            {
                "product_tmpl_id": template.id,
                "attribute_id": attribute.id,
                "value_ids": [Command.set(attribute.value_ids.ids)],
            }
        )
        line.action_archive()
        return line

    def test_create_returns_records_in_vals_list_order(self):
        tmpl_new, tmpl_archived = self.env["product.template"].create(
            [{"name": "OrderNew"}, {"name": "OrderArchived"}]
        )
        self._archived_line(tmpl_archived, self.attr_color)

        vals_list = [
            {
                "product_tmpl_id": tmpl_new.id,
                "attribute_id": self.attr_size.id,
                "value_ids": [Command.set(self.attr_size.value_ids.ids)],
            },
            {
                "product_tmpl_id": tmpl_archived.id,
                "attribute_id": self.attr_color.id,
                "value_ids": [Command.set(self.attr_color.value_ids.ids)],
            },
        ]
        lines = self.env["product.template.attribute.line"].create(vals_list)

        self.assertEqual(
            lines.mapped("product_tmpl_id"),
            tmpl_new | tmpl_archived,
            "create() must return one record per vals, in the same order",
        )
        for vals, line in zip(vals_list, lines, strict=True):
            self.assertEqual(line.product_tmpl_id.id, vals["product_tmpl_id"])
            self.assertEqual(line.attribute_id.id, vals["attribute_id"])

    def test_create_order_with_archived_line_first(self):
        tmpl_archived, tmpl_new = self.env["product.template"].create(
            [{"name": "OrderArchivedFirst"}, {"name": "OrderNewSecond"}]
        )
        self._archived_line(tmpl_archived, self.attr_color)

        lines = self.env["product.template.attribute.line"].create(
            [
                {
                    "product_tmpl_id": tmpl_archived.id,
                    "attribute_id": self.attr_color.id,
                    "value_ids": [Command.set(self.attr_color.value_ids.ids)],
                },
                {
                    "product_tmpl_id": tmpl_new.id,
                    "attribute_id": self.attr_size.id,
                    "value_ids": [Command.set(self.attr_size.value_ids.ids)],
                },
            ]
        )
        self.assertEqual(lines.mapped("product_tmpl_id"), tmpl_archived | tmpl_new)

    def test_import_products_onto_template_with_archived_line(self):
        tmpl_new, tmpl_archived = self.env["product.template"].create(
            [{"name": "ImportNew"}, {"name": "ImportArchived"}]
        )
        self._archived_line(tmpl_archived, self.attr_size)

        result = self.env["product.template"].load(
            ["name", "import_attribute_values"],
            [
                ["ImportNew", "OrderColor:OrderRed"],
                ["ImportArchived", "OrderSize:OrderBig"],
            ],
        )
        errors = [m for m in result["messages"] if m["type"] == "error"]
        self.assertFalse(errors, f"import reported errors: {errors}")
        self.assertTrue(result["ids"], "import created nothing")

        for template, attribute, value_name in (
            (tmpl_new, self.attr_color, "OrderRed"),
            (tmpl_archived, self.attr_size, "OrderBig"),
        ):
            name = template.name
            self.assertEqual(
                template.attribute_line_ids.attribute_id,
                attribute,
                f"{name} got the wrong attribute line",
            )
            variant = template.product_variant_ids
            self.assertEqual(len(variant), 1)
            ptav = variant.product_template_attribute_value_ids
            self.assertEqual(len(ptav), 1, f"{name}: variant has no attribute value")
            self.assertEqual(ptav.name, value_name)
            self.assertEqual(
                ptav.product_tmpl_id,
                template,
                f"{name}: variant carries a value owned by another template",
            )


@tagged("post_install", "-at_install")
class TestTemplateCopyPriceExtra(ProductCommon):
    def test_copy_preserves_price_extra_with_archived_value(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "CopyColor",
                "create_variant": "always",
                "value_ids": [
                    Command.create({"name": "CopyRed"}),
                    Command.create({"name": "CopyBlue"}),
                    Command.create({"name": "CopyGreen"}),
                ],
            }
        )
        red, blue, green = attribute.value_ids
        template = self.env["product.template"].create(
            {
                "name": "Copy source",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set(attribute.value_ids.ids)],
                        }
                    )
                ],
            }
        )
        line = template.attribute_line_ids

        red_variant = template.product_variant_ids.filtered(
            lambda variant: (
                variant.product_template_attribute_value_ids.product_attribute_value_id
                == red
            )
        )
        self.env["product.combo"].create(
            {
                "name": "Blocking combo",
                "combo_item_ids": [Command.create({"product_id": red_variant.id})],
            }
        )
        line.value_ids = [Command.unlink(red.id)]
        self.assertFalse(
            line.product_template_value_ids.filtered(
                lambda ptav: ptav.product_attribute_value_id == red
            ).ptav_active,
            "test setup: the red value should be archived, not deleted",
        )

        extras = {blue: 11.0, green: 22.0}
        for ptav in line.product_template_value_ids._filtered_active():
            ptav.price_extra = extras[ptav.product_attribute_value_id]

        copied = template.copy()
        copied_extras = {
            ptav.product_attribute_value_id: ptav.price_extra
            for ptav in copied.attribute_line_ids.product_template_value_ids._filtered_active()
        }
        self.assertEqual(
            copied_extras,
            extras,
            "duplicating a template must preserve the extra price of every value",
        )


@tagged("post_install", "-at_install")
class TestSellerPriceUomConversion(ProductCommon):
    def test_price_discounted_with_incompatible_vendor_uom(self):
        template = self._create_product(
            name="Cross category seller product", uom_id=self.uom_unit.id
        ).product_tmpl_id
        vendor = self.env["res.partner"].create({"name": "Cross category vendor"})
        seller = self.env["product.supplierinfo"].create(
            {
                "partner_id": vendor.id,
                "product_tmpl_id": template.id,
                "product_uom_id": self.uom_kgm.id,
                "price": 100.0,
                "min_qty": 0.0,
            }
        )
        self.assertFalse(self.uom_kgm._has_common_reference(self.uom_unit))
        self.assertEqual(
            seller.price_discounted,
            100.0,
            "an unconvertible vendor unit must leave the price untouched,"
            " not scale it by the ratio of two unrelated factors",
        )

    def test_price_discounted_with_compatible_vendor_uom(self):
        template = self._create_product(
            name="Same category seller product", uom_id=self.uom_unit.id
        ).product_tmpl_id
        vendor = self.env["res.partner"].create({"name": "Dozen vendor"})
        seller = self.env["product.supplierinfo"].create(
            {
                "partner_id": vendor.id,
                "product_tmpl_id": template.id,
                "product_uom_id": self.uom_dozen.id,
                "price": 120.0,
                "min_qty": 0.0,
            }
        )
        self.assertEqual(seller.price_discounted, 10.0)

    def test_compute_price_is_strict_by_default(self):
        with self.assertRaises(UserError):
            self.uom_kgm._get_price_in_unit(100.0, self.uom_unit)

    def test_compute_price_wrappers_degrade(self):
        self.assertEqual(
            self.uom_kgm._get_price_report(100.0, self.uom_unit), 100.0
        )
        self.assertEqual(
            self.uom_kgm._get_price_estimate(100.0, self.uom_unit), 100.0
        )
        self.assertEqual(
            self.uom_dozen._get_price_report(120.0, self.uom_unit), 10.0
        )


@tagged("post_install", "-at_install")
class TestTemplateBarcodeCheckBatching(ProductCommon):
    def _count_check_queries(self, size, tag):
        templates = self.env["product.template"].create(
            [
                {"name": f"Batched {tag} {i}", "barcode": f"BATCH-{tag}-{i:05d}"}
                for i in range(size)
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        templates._check_barcode_uniqueness()
        return self.env.cr.sql_statement_count - before

    def test_barcode_constraint_does_not_scale_with_batch_size(self):
        small = self._count_check_queries(5, "small")
        large = self._count_check_queries(50, "large")
        self.assertEqual(
            small,
            large,
            f"barcode check cost scales with batch size ({small} -> {large} queries)",
        )

    def test_barcode_constraint_still_detects_collisions(self):
        other_company = self.env["res.company"].create({"name": "Barcode Co"})
        self.env.user.company_ids = [Command.link(other_company.id)]
        first = self.env["product.template"].create(
            {
                "name": "Barcode A",
                "barcode": "COLLIDE-1",
                "company_id": self.env.company.id,
            }
        )
        second = self.env["product.template"].create(
            {
                "name": "Barcode B",
                "barcode": "COLLIDE-1",
                "company_id": other_company.id,
            }
        )
        self.assertTrue(first and second, "cross-company reuse must stay allowed")
        with self.assertRaises(Exception):
            second.write({"company_id": self.env.company.id})
            self.env.flush_all()
