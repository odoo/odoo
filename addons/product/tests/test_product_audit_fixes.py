from types import SimpleNamespace

import psycopg

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.product.tests.common import ProductCommon


@tagged("post_install", "-at_install")
class TestProductAuditFixes(ProductCommon):
    def test_attribute_line_write_does_not_mutate_caller_vals(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "MutAttr",
                "value_ids": [
                    Command.create({"name": "a"}),
                    Command.create({"name": "b"}),
                ],
            }
        )
        template = self.env["product.template"].create(
            {
                "name": "MutProbe",
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
        vals = {"active": False}
        template.attribute_line_ids.write(vals)
        self.assertEqual(vals, {"active": False})

    def test_supplierinfo_create_does_not_mutate_caller_vals(self):
        vendor = self.env["res.partner"].create({"name": "MutVendor"})
        vals = {
            "partner_id": vendor.id,
            "product_id": self.product.id,
            "price": 1.0,
        }
        self.env["product.supplierinfo"].create([vals])
        self.assertNotIn("product_tmpl_id", vals)

    def test_pricelist_item_create_and_write_do_not_mutate_caller_vals(self):
        vals = {
            "pricelist_id": self.pricelist.id,
            "product_id": self.product.id,
            "compute_price": "fixed",
            "fixed_price": 1.0,
        }
        expected = dict(vals)
        item = self.env["product.pricelist.item"].create([vals])
        self.assertEqual(vals, expected)
        self.assertEqual(item.applied_on, "0_product_variant")
        self.assertEqual(item.product_tmpl_id, self.product.product_tmpl_id)

        write_vals = {"applied_on": "3_global"}
        item.write(write_vals)
        self.assertEqual(write_vals, {"applied_on": "3_global"})
        self.assertFalse(item.product_id)

    def test_settings_save_does_not_archive_pricelists_when_already_disabled(self):
        # The toggle is a group implied on base.group_user, and that implication
        # is what res.config.settings reads back. Dropping the group from the
        # current user leaves the feature on, so turn it off the way the
        # settings themselves do, before there is a pricelist to lose.
        self.env["res.config.settings"].create(
            {"group_product_pricelist": False}
        ).execute()
        pricelist = self.env["product.pricelist"].create({"name": "SurvivorPL"})

        settings = self.env["res.config.settings"].create({})
        self.assertFalse(
            settings.group_product_pricelist, "sanity: feature is already off"
        )
        settings.set_values()

        self.assertTrue(
            pricelist.active,
            "an unrelated settings save must not archive existing pricelists",
        )

    def test_disabling_pricelist_feature_still_archives(self):
        self.env["res.config.settings"].create(
            {"group_product_pricelist": True}
        ).execute()
        pricelist = self.env["product.pricelist"].create({"name": "ToArchivePL"})

        settings = self.env["res.config.settings"].create({})
        self.assertTrue(settings.group_product_pricelist, "sanity: feature is on")
        settings.group_product_pricelist = False
        settings.set_values()

        self.assertFalse(
            pricelist.active, "disabling the feature must archive active pricelists"
        )

    def test_archived_attribute_line_is_reactivated_not_duplicated(self):
        attribute = self.env["product.attribute"].create(
            {"name": "ReuseColor", "value_ids": [Command.create({"name": "R"})]}
        )
        template = self.env["product.template"].create(
            {
                "name": "ReuseProbe",
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
        line.active = False
        self.env.flush_all()

        template.write(
            {
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set(attribute.value_ids.ids)],
                        }
                    )
                ]
            }
        )
        self.env.flush_all()
        self.assertEqual(
            len(
                template.attribute_line_ids.filtered(
                    lambda l: l.attribute_id == attribute
                )
            ),
            1,
        )

    def test_duplicate_tag_name_rejected(self):
        self.env["product.tag"].create({"name": "DupTag"})
        with self.assertRaises(ValidationError):
            self.env["product.tag"].create({"name": "DupTag"})
            self.env.flush_all()

    def test_duplicate_tag_name_rejected_across_translations(self):
        self.env["res.lang"]._activate_lang("es_MX")
        tag = self.env["product.tag"].create({"name": "TransTag"})
        tag.with_context(lang="es_MX").name = "Frágil"
        self.env.flush_all()

        with self.assertRaises(ValidationError):
            self.env["product.tag"].create({"name": "TransTag"})
            self.env.flush_all()

    def test_unlinking_last_combo_item_rejected(self):
        product = (
            self.env["product.template"]
            .create({"name": "ComboChoice", "list_price": 5.0})
            .product_variant_id
        )
        combo = self.env["product.combo"].create(
            {
                "name": "AuditCombo",
                "combo_item_ids": [Command.create({"product_id": product.id})],
            }
        )
        with self.assertRaises(ValidationError):
            combo.combo_item_ids.unlink()
            self.env.cr.flush()

    def test_replacing_all_combo_items_in_one_write_is_allowed(self):
        products = (
            self.env["product.template"]
            .create(
                [
                    {"name": "ComboA", "list_price": 5.0},
                    {"name": "ComboB", "list_price": 7.0},
                ]
            )
            .product_variant_id
        )
        combo = self.env["product.combo"].create(
            {
                "name": "SwapCombo",
                "combo_item_ids": [Command.create({"product_id": products[0].id})],
            }
        )
        combo.write(
            {
                "combo_item_ids": [
                    Command.delete(combo.combo_item_ids.id),
                    Command.create({"product_id": products[1].id}),
                ]
            }
        )
        self.env.cr.flush()
        self.assertEqual(combo.combo_item_ids.product_id, products[1])

    def test_deleting_combo_cascades_to_its_items(self):
        product = (
            self.env["product.template"]
            .create({"name": "ComboGone", "list_price": 5.0})
            .product_variant_id
        )
        combo = self.env["product.combo"].create(
            {
                "name": "DoomedCombo",
                "combo_item_ids": [Command.create({"product_id": product.id})],
            }
        )
        combo.unlink()
        self.env.cr.flush()
        self.assertFalse(combo.exists())

    def test_product_count_refreshes_when_product_changes_category(self):
        Category = self.env["product.category"]
        source = Category.create({"name": "CountSource"})
        target = Category.create({"name": "CountTarget"})
        template = self.env["product.template"].create(
            {"name": "CountProbe", "categ_id": source.id}
        )
        self.assertEqual(source.product_count, 1)
        self.assertEqual(target.product_count, 0)

        template.categ_id = target
        self.env.flush_all()

        self.assertEqual(source.product_count, 0, "source count must drop")
        self.assertEqual(target.product_count, 1, "target count must rise")

    def test_packaging_barcode_is_unique_per_company_not_globally(self):
        company_a = self.env["res.company"].create({"name": "PkgCoA"})
        company_b = self.env["res.company"].create({"name": "PkgCoB"})
        uom = self.env.ref("uom.product_uom_unit")
        products = {}
        for company in (company_a, company_b):
            template = self.env["product.template"].create(
                {"name": f"Pkg-{company.name}", "company_id": company.id}
            )
            products[company] = template.product_variant_id

        self.env["product.uom"].create(
            {
                "product_id": products[company_a].id,
                "uom_id": uom.id,
                "barcode": "SHARED-BC",
                "company_id": company_a.id,
            }
        )
        self.env["product.uom"].create(
            {
                "product_id": products[company_b].id,
                "uom_id": uom.id,
                "barcode": "SHARED-BC",
                "company_id": company_b.id,
            }
        )
        self.env.flush_all()

    def test_packaging_barcode_still_unique_within_a_company(self):
        company = self.env["res.company"].create({"name": "PkgCoSolo"})
        uom = self.env.ref("uom.product_uom_unit")
        template = self.env["product.template"].create(
            {"name": "PkgSolo", "company_id": company.id}
        )
        self.env["product.uom"].create(
            {
                "product_id": template.product_variant_id.id,
                "uom_id": uom.id,
                "barcode": "SOLO-BC",
                "company_id": company.id,
            }
        )
        self.env.flush_all()
        with self.assertRaises(Exception):
            self.env["product.uom"].create(
                {
                    "product_id": template.product_variant_id.id,
                    "uom_id": uom.id,
                    "barcode": "SOLO-BC",
                    "company_id": company.id,
                }
            )
            self.env.flush_all()

    def test_product_barcode_collides_with_same_company_packaging(self):
        company = self.env["res.company"].create({"name": "PkgCoSym"})
        uom = self.env.ref("uom.product_uom_unit")
        template = self.env["product.template"].create(
            {"name": "SymHolder", "company_id": company.id}
        )
        self.env["product.uom"].create(
            {
                "product_id": template.product_variant_id.id,
                "uom_id": uom.id,
                "barcode": "SYM-BC",
                "company_id": company.id,
            }
        )
        self.env.flush_all()
        with self.assertRaises(ValidationError):
            self.env["product.template"].create(
                {
                    "name": "SymProduct",
                    "company_id": company.id,
                    "barcode": "SYM-BC",
                }
            )
            self.env.flush_all()

    def test_packaging_not_visible_across_companies(self):
        company_a = self.env["res.company"].create({"name": "RuleCoA"})
        company_b = self.env["res.company"].create({"name": "RuleCoB"})
        uom = self.env.ref("uom.product_uom_unit")
        template = self.env["product.template"].create(
            {"name": "SecretPkg", "company_id": company_b.id}
        )
        packaging = self.env["product.uom"].create(
            {
                "product_id": template.product_variant_id.id,
                "uom_id": uom.id,
                "barcode": "SECRET-PKG",
                "company_id": company_b.id,
            }
        )
        self.env.flush_all()

        user = new_test_user(self.env, login="rule_emp", groups="base.group_user")
        user.write(
            {"company_ids": [Command.set([company_a.id])], "company_id": company_a.id}
        )

        self.assertFalse(
            self.env["product.uom"].with_user(user).search([("id", "=", packaging.id)]),
            "another company's packaging must not be visible",
        )

    def test_combo_item_not_visible_across_companies(self):
        company_a = self.env["res.company"].create({"name": "RuleComboA"})
        company_b = self.env["res.company"].create({"name": "RuleComboB"})
        choice = (
            self.env["product.template"]
            .create(
                {"name": "ComboChoiceB", "company_id": company_b.id, "list_price": 9.0}
            )
            .product_variant_id
        )
        combo = (
            self.env["product.combo"]
            .with_company(company_b)
            .create(
                {
                    "name": "SecretCombo",
                    "company_id": company_b.id,
                    "combo_item_ids": [Command.create({"product_id": choice.id})],
                }
            )
        )
        self.env.flush_all()

        user = new_test_user(self.env, login="rule_emp2", groups="base.group_user")
        user.write(
            {"company_ids": [Command.set([company_a.id])], "company_id": company_a.id}
        )

        self.assertFalse(
            self.env["product.combo.item"]
            .with_user(user)
            .search([("id", "=", combo.combo_item_ids.id)]),
            "another company's combo items must not be visible",
        )

    def test_label_layout_wizard_is_private_to_its_creator(self):
        user_a = new_test_user(self.env, login="label_a", groups="base.group_user")
        user_b = new_test_user(self.env, login="label_b", groups="base.group_user")
        wizard = (
            self.env["product.label.layout"]
            .with_user(user_a)
            .create({"print_format": "4x7xprice"})
        )
        self.env.flush_all()

        with self.assertRaises(AccessError):
            self.env["product.label.layout"].with_user(user_b).browse(wizard.id).read(
                ["print_format"]
            )

    def test_variant_value_alias_keeps_combination_indices_in_sync(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "AliasColor",
                "value_ids": [
                    Command.create({"name": "R"}),
                    Command.create({"name": "B"}),
                ],
            }
        )
        template = self.env["product.template"].create(
            {
                "name": "AliasProbe",
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
        first, second = template.product_variant_ids
        target = second.product_template_attribute_value_ids

        try:
            first.write(
                {"product_template_variant_value_ids": [Command.set(target.ids)]}
            )
            self.env.flush_all()
        except Exception:
            return
        self.env.invalidate_all()
        self.assertEqual(
            first.combination_indices,
            first.product_template_attribute_value_ids._ids2str(),
            "combination_indices must match the relation it indexes",
        )

    def test_variant_value_alias_is_readonly(self):
        field = self.env["product.product"]._fields[
            "product_template_variant_value_ids"
        ]
        self.assertTrue(field.readonly)

    def test_price_in_incompatible_uom_raises(self):
        liter = self.env.ref("uom.product_uom_litre", raise_if_not_found=False)
        if not liter:
            self.skipTest("liter UoM not available")
        template = self.env["product.template"].create(
            {"name": "UomProbe", "list_price": 10.0}
        )
        self.assertFalse(
            template.uom_id._has_common_reference(liter), "sanity: incompatible units"
        )
        with self.assertRaises(UserError):
            template._get_prices("list_price", uom=liter)
        with self.assertRaises(UserError):
            template.product_variant_id._get_prices("list_price", uom=liter)

    def test_price_in_compatible_uom_still_converts(self):
        dozen = self.env.ref("uom.product_uom_dozen")
        unit = self.env.ref("uom.product_uom_unit")
        template = self.env["product.template"].create(
            {"name": "UomOk", "list_price": 12.0, "uom_id": unit.id}
        )
        self.assertAlmostEqual(
            template._get_prices("list_price", uom=dozen)[template.id],
            unit._get_price_in_unit(12.0, dozen),
            places=6,
        )

    def test_invalid_variant_limit_parameter_is_tolerated(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "product.dynamic_variant_limit", "not-a-number"
        )
        attribute = self.env["product.attribute"].create(
            {"name": "LimitAttr", "value_ids": [Command.create({"name": "x"})]}
        )
        template = self.env["product.template"].create(
            {
                "name": "LimitProbe",
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
        self.assertTrue(template.product_variant_ids)

    def test_catalog_action_drops_caller_defaults(self):
        order = self.env["mixin.product.catalog"]
        context = {
            "default_partner_id": 42,
            "default_name": "SO0001",
            "allowed_company_ids": [self.env.company.id],
        }
        forwarded = order.with_context(**context)._prepare_catalog_action_context()
        self.assertNotIn("default_partner_id", forwarded)
        self.assertNotIn("default_name", forwarded)
        self.assertIn(
            "allowed_company_ids", forwarded, "non-default keys must be preserved"
        )

    def test_pricelist_report_rejects_oversized_product_list(self):
        Report = self.env["report.product.report_pricelist"]
        with self.assertRaises(UserError):
            Report._prepare_pricelist_rendering_context(
                {
                    "active_model": "product.template",
                    "active_ids": list(range(Report.MAX_PRODUCTS + 1)),
                    "quantities": [1],
                }
            )

    def test_pricelist_report_rejects_oversized_product_by_quantity_combo(self):
        Report = self.env["report.product.report_pricelist"]
        templates = self.env["product.template"].create(
            [{"name": f"ComboProbe{i}"} for i in range(100)]
        )
        quantities = list(range(1, 52))  # 100 * 51 > MAX_PRICE_COMPUTATIONS (5000)
        self.assertLessEqual(len(templates), Report.MAX_PRODUCTS)
        self.assertLessEqual(len(quantities), Report.MAX_QUANTITIES)
        with self.assertRaises(UserError):
            Report._get_products_data(True, templates, self.pricelist, quantities)

    def test_pricelist_report_batches_price_computation(self):
        Report = self.env["report.product.report_pricelist"]
        pricelist = self.env["product.pricelist"].create({"name": "ReportPL"})
        templates = self.env["product.template"].create(
            [{"name": f"ReportProbe{i}", "list_price": 10.0 + i} for i in range(20)]
        )
        self.env.flush_all()

        def query_count(products):
            self.env.invalidate_all()
            before = self.env.cr.sql_statement_count
            Report._prepare_pricelist_rendering_context(
                {
                    "active_model": "product.template",
                    "active_ids": products.ids,
                    "pricelist_id": pricelist.id,
                    "quantities": [1, 2, 3, 4, 5],
                }
            )
            return self.env.cr.sql_statement_count - before

        few = query_count(templates[:5])
        many = query_count(templates)
        self.assertLess(
            many,
            few * 2,
            "query count must not scale with the number of products "
            f"(5 products: {few} queries, 20 products: {many})",
        )

    def test_pricelist_report_prices_are_unchanged_by_batching(self):
        Report = self.env["report.product.report_pricelist"]
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "ReportValuesPL",
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "compute_price": "percentage",
                            "percent_price": 10,
                        }
                    )
                ],
            }
        )
        templates = self.env["product.template"].create(
            [{"name": f"ValueProbe{i}", "list_price": 100.0 + i} for i in range(3)]
        )
        self.env.flush_all()

        data = Report._prepare_pricelist_rendering_context(
            {
                "active_model": "product.template",
                "active_ids": templates.ids,
                "pricelist_id": pricelist.id,
                "quantities": [1, 4],
            }
        )
        by_id = {row["id"]: row for row in data["products"]}
        for template in templates:
            for qty in (1, 4):
                self.assertAlmostEqual(
                    by_id[template.id]["price"][qty],
                    pricelist._get_product_price(template, qty),
                    places=6,
                )

    def test_attribute_config_not_visible_across_companies(self):
        company_a = self.env["res.company"].create({"name": "AttrCo A"})
        company_b = self.env["res.company"].create({"name": "AttrCo B"})
        attribute = self.env["product.attribute"].create(
            {
                "name": "LeakAttr",
                "value_ids": [
                    Command.create({"name": "Secret"}),
                    Command.create({"name": "Other"}),
                ],
            }
        )
        template = (
            self.env["product.template"]
            .with_company(company_a)
            .create(
                {
                    "name": "AttrCo A Product",
                    "company_id": company_a.id,
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
        )
        values = template.attribute_line_ids.product_template_value_ids
        values[0].price_extra = 123.45
        self.env.flush_all()

        user_b = new_test_user(
            self.env,
            login="attrco_b",
            groups="base.group_user",
            company_id=company_b.id,
            company_ids=[Command.set([company_b.id])],
        )
        env_b = self.env(user=user_b, su=False)

        self.assertFalse(
            env_b["product.template"].search([("id", "=", template.id)]),
            "sanity: the template itself is already hidden",
        )
        self.assertFalse(
            env_b["product.template.attribute.line"].search(
                [("product_tmpl_id", "=", template.id)]
            ),
            "its attribute lines must be hidden too",
        )
        self.assertFalse(
            env_b["product.template.attribute.value"].search(
                [("id", "in", values.ids)]
            ),
            "its attribute values (and their price_extra) must be hidden too",
        )

    def test_tag_name_uniqueness_still_holds_when_batched(self):
        Tag = self.env["product.tag"]
        Tag.create({"name": "BatchTagA"})

        with self.assertRaises(ValidationError):
            Tag.create({"name": "BatchTagA"})

        with self.assertRaises(ValidationError):
            Tag.create([{"name": "BatchTagB"}, {"name": "BatchTagB"}])

        tags = Tag.create([{"name": "BatchTagC"}, {"name": "BatchTagD"}])
        tags[0].name = "BatchTagC"

    def test_chained_fixed_rule_does_not_evaluate_its_base_pricelist(self):
        self._enable_pricelists()
        base_pricelist = self.env["product.pricelist"].create(
            {
                "name": "ChainBase",
                "item_ids": [
                    Command.create(
                        {"compute_price": "percentage", "percent_price": 50.0}
                    )
                ],
            }
        )
        top_pricelist = self.env["product.pricelist"].create(
            {
                "name": "ChainTop",
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "fixed",
                            "fixed_price": 7.0,
                            "base": "pricelist",
                            "base_pricelist_id": base_pricelist.id,
                        }
                    )
                ],
            }
        )

        from unittest.mock import patch

        Pricelist = type(self.env["product.pricelist"])
        real = Pricelist._get_applicable_rules
        touched = []

        def spy(self, *args, **kwargs):
            touched.extend(self.ids)
            return real(self, *args, **kwargs)

        with patch.object(Pricelist, "_get_applicable_rules", spy):
            price = top_pricelist._get_product_price(self.product, 1.0)

        self.assertEqual(price, 7.0, "the fixed amount still wins")
        self.assertNotIn(
            base_pricelist.id,
            touched,
            "the base pricelist must not be evaluated for a fixed rule",
        )

    def test_chained_formula_rule_still_evaluates_its_base_pricelist(self):
        self._enable_pricelists()
        base_pricelist = self.env["product.pricelist"].create(
            {
                "name": "ChainBase2",
                "item_ids": [
                    Command.create(
                        {"compute_price": "percentage", "percent_price": 50.0}
                    )
                ],
            }
        )
        top_pricelist = self.env["product.pricelist"].create(
            {
                "name": "ChainTop2",
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "formula",
                            "base": "pricelist",
                            "base_pricelist_id": base_pricelist.id,
                            "price_discount": 10.0,
                        }
                    )
                ],
            }
        )
        self.assertAlmostEqual(
            top_pricelist._get_product_price(self.product, 1.0), 9.0, places=6
        )

    def test_value_archived_by_one_line_is_revived_by_a_later_one(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "PoolAttr",
                "create_variant": "no_variant",
                "value_ids": [
                    Command.create({"name": "X"}),
                    Command.create({"name": "Y"}),
                    Command.create({"name": "Z"}),
                ],
            }
        )
        value_x, value_y, value_z = attribute.value_ids
        template = self.env["product.template"].create(
            {
                "name": "PoolProbe",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set((value_x + value_y).ids)],
                        }
                    ),
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set(value_z.ids)],
                        }
                    ),
                ],
            }
        )
        first_line, second_line = template.attribute_line_ids
        value_for_x = first_line.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == value_x
        )
        value_for_x.price_extra = 42.0
        original_id = value_for_x.id

        no_sync = {"update_product_template_attribute_values": False}
        first_line.with_context(**no_sync).write(
            {"value_ids": [Command.set(value_y.ids)]}
        )
        second_line.with_context(**no_sync).write(
            {"value_ids": [Command.set((value_z + value_x).ids)]}
        )
        self.env.flush_all()
        (first_line + second_line)._update_product_template_attribute_values()
        self.env.flush_all()
        self.env.invalidate_all()

        values_for_x = self.env["product.template.attribute.value"].search(
            [
                ("product_tmpl_id", "=", template.id),
                ("product_attribute_value_id", "=", value_x.id),
            ]
        )
        self.assertEqual(len(values_for_x), 1, "no duplicate value may be created")
        self.assertEqual(
            values_for_x.id, original_id, "the existing record must be revived"
        )
        self.assertEqual(values_for_x.attribute_line_id, second_line)
        self.assertTrue(values_for_x.ptav_active)
        self.assertEqual(values_for_x.price_extra, 42.0, "its configuration survives")

    def test_reactivation_respects_the_variant_generation_opt_out(self):
        template = self.env["product.template"].create({"name": "OptOutProbe"})
        variant = template.product_variant_id
        template.action_archive()
        self.env.flush_all()
        self.assertFalse(variant.active, "sanity: archiving the template archived it")
        self.assertFalse(
            template.product_variant_ids, "sanity: no *active* variant is left"
        )

        template.with_context(create_product_product=False).write({"active": True})
        self.env.flush_all()
        self.assertFalse(
            variant.active,
            "the opt-out must be honoured on reactivation too",
        )

        template.write({"active": True})
        self.env.flush_all()
        self.assertTrue(variant.active)

    def test_deleting_value_used_on_archived_template_archives_it(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "ArchAttr",
                "create_variant": "no_variant",
                "value_ids": [
                    Command.create({"name": "Engraving"}),
                    Command.create({"name": "Plain"}),
                ],
            }
        )
        template = self.env["product.template"].create(
            {
                "name": "ArchProbe",
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
        template.action_archive()
        self.env.flush_all()

        value = attribute.value_ids[0]
        value.unlink()
        self.env.flush_all()

        self.assertTrue(value.exists(), "the value must survive as archived")
        self.assertFalse(value.active)

    def test_deleting_value_left_on_an_archived_variant_archives_it(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "ArchVariantAttr",
                "create_variant": "always",
                "value_ids": [
                    Command.create({"name": "Red"}),
                    Command.create({"name": "Blue"}),
                ],
            }
        )
        red, blue = attribute.value_ids
        template = self.env["product.template"].create(
            {
                "name": "ArchVariantProbe",
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
        red_ptav = line.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == red
        )
        red_variant = red_ptav.ptav_product_variant_ids
        red_variant.action_archive()

        line.with_context(update_product_template_attribute_values=False).write(
            {"value_ids": [Command.set(blue.ids)]}
        )
        red_ptav.ptav_active = False
        self.env.flush_all()

        self.assertFalse(red.is_used_on_products, "sanity: no active line uses it")
        self.assertEqual(
            red_ptav.with_context(active_test=False).ptav_product_variant_ids,
            red_variant,
            "sanity: the archived variant still carries the value",
        )

        red.unlink()
        self.env.flush_all()

        self.assertTrue(red.exists(), "the value must survive as archived")
        self.assertFalse(red.active)

    def test_deleting_value_an_active_product_still_offers_raises(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "LiveLineAttr",
                "create_variant": "always",
                "value_ids": [
                    Command.create({"name": "Red"}),
                    Command.create({"name": "Blue"}),
                ],
            }
        )
        red = attribute.value_ids[0]
        template = self.env["product.template"].create(
            {
                "name": "LiveLineProbe",
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
        red_ptav = line.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == red
        )
        red_variant = red_ptav.ptav_product_variant_ids
        red_variant.action_archive()
        self.env.flush_all()

        self.assertTrue(red.is_used_on_products, "sanity: an active line offers it")
        with self.assertRaises(UserError):
            red.unlink()

        self.env.invalidate_all()
        self.assertTrue(red.active)
        self.assertEqual(line.value_ids, attribute.value_ids)
        self.assertEqual(line.value_count, 2)

    def test_deleting_unused_value_still_deletes(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "FreeAttr",
                "value_ids": [
                    Command.create({"name": "A"}),
                    Command.create({"name": "B"}),
                ],
            }
        )
        value = attribute.value_ids[0]
        value.unlink()
        self.env.flush_all()
        self.assertFalse(value.exists(), "an unused value must be deleted outright")

    def _catalog_controller(self):
        from unittest.mock import patch

        from odoo.addons.product.controllers import catalog

        return patch.object(
            catalog, "request", SimpleNamespace(env=self.env)
        ), catalog.ProductCatalogController

    def test_catalog_get_order_rejects_unknown_model(self):
        request_patch, controller = self._catalog_controller()
        with request_patch, self.assertRaises(UserError):
            controller._get_order("res.partner", 1)

    def test_catalog_get_order_rejects_non_numeric_id(self):
        request_patch, controller = self._catalog_controller()
        with request_patch, self.assertRaises(UserError):
            controller._get_order("mixin.product.catalog", "not-an-int")

    def _template_with_two_costed_variants(self, name):
        attribute = self.env["product.attribute"].create(
            {
                "name": f"{name}Attr",
                "value_ids": [
                    Command.create({"name": "one"}),
                    Command.create({"name": "two"}),
                ],
            }
        )
        template = self.env["product.template"].create(
            {
                "name": name,
                "list_price": 0.0,
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
        self.assertEqual(len(template.product_variant_ids), 2)
        return template

    def test_multi_variant_template_cost_falls_back_to_first_variant(self):
        template = self._template_with_two_costed_variants("CostFallback")
        first, second = template.product_variant_ids
        first.standard_price = 10.0
        second.standard_price = 999.0
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(template.standard_price, 0.0, "template mirrors no variant")
        self.assertAlmostEqual(
            template._get_prices("standard_price")[template.id], 10.0, places=2
        )

    def test_multi_variant_template_cost_follows_variant_order(self):
        template = self._template_with_two_costed_variants("CostOrder")
        first, second = template.product_variant_ids
        first.standard_price = 10.0
        second.standard_price = 999.0
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertAlmostEqual(
            template._get_prices("standard_price")[template.id], 10.0, places=2
        )

        second.default_code = "AAA-first"
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertAlmostEqual(
            template._get_prices("standard_price")[template.id],
            999.0,
            places=2,
            msg="cost basis follows variant ordering, not any cost edit",
        )

    def _warm_caches(self, template):
        self.env["ir.rule"]._get_domain_accessible_records("product.template", "read")
        self.env["ir.rule"]._get_domain_accessible_records("res.partner", "read")
        self.env["ir.model.access"].check("product.template", "read", False)
        template._get_first_possible_variant_id()

    def test_variant_cache_invalidation_spares_unrelated_caches(self):
        lrus = self.env.registry.ormcache_lrus
        template = self.env["product.template"].create({"name": "CacheScopeProbe"})
        self.env.flush_all()
        self._warm_caches(template)

        default_before = set(lrus["default"])
        variants_before = len(lrus["product_variants"])
        self.assertTrue(default_before, "sanity: 'default' is warm")
        self.assertTrue(variants_before, "sanity: 'product_variants' is warm")

        template.product_variant_id.write({"active": False})

        self.assertLessEqual(
            default_before,
            set(lrus["default"]),
            "archiving a variant must not evict unrelated 'default' caches",
        )
        self.assertEqual(
            len(lrus["product_variants"]), 0, "variant lookups must be invalidated"
        )

    def test_clearing_default_still_clears_variant_caches(self):
        lrus = self.env.registry.ormcache_lrus
        template = self.env["product.template"].create({"name": "CacheCompatProbe"})
        self.env.flush_all()
        self._warm_caches(template)
        self.assertTrue(len(lrus["product_variants"]), "sanity: warm")

        self.env.registry.clear_cache()

        self.assertEqual(len(lrus["product_variants"]), 0)

    def test_pricing_follows_the_environment_company_not_the_pricelist_owner(self):
        usd = self.env.ref("base.USD")
        usd.active = True
        company_a = self.env["res.company"].create(
            {"name": "PriceCtxA", "currency_id": usd.id}
        )
        company_b = self.env["res.company"].create(
            {"name": "PriceCtxB", "currency_id": usd.id}
        )
        template = self.env["product.template"].create(
            {"name": "PriceCtxProbe", "list_price": 5.0}
        )
        product = template.product_variant_id
        product.with_company(company_a).standard_price = 10.0
        product.with_company(company_b).standard_price = 70.0
        self.env.flush_all()

        pricelist = self.env["product.pricelist"].create(
            {
                "name": "CtxPL",
                "company_id": company_b.id,
                "currency_id": usd.id,
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "base": "standard_price",
                            "compute_price": "formula",
                            "price_discount": 0.0,
                        }
                    )
                ],
            }
        )
        self.env.flush_all()

        self.env.invalidate_all()
        price_from_a = pricelist._get_product_price(
            product.with_company(company_a), 1.0
        )
        self.env.invalidate_all()
        price_from_b = pricelist._get_product_price(
            product.with_company(company_b), 1.0
        )

        self.assertAlmostEqual(price_from_a, 10.0, places=2)
        self.assertAlmostEqual(price_from_b, 70.0, places=2)

    def _spanish_product(self):
        self.env["res.lang"]._activate_lang("es_MX")
        template = self.env["product.template"].create({"name": "Blue Widget"})
        template.with_context(lang="es_MX").name = "Artilugio Azul"
        self.env.flush_all()
        return template

    def test_duplicating_in_one_language_suffixes_every_language(self):
        template = self._spanish_product()

        copy = template.with_context(lang="es_MX").copy()
        self.env.flush_all()

        name_en = copy.with_context(lang="en_US").name
        name_es = copy.with_context(lang="es_MX").name
        self.assertNotEqual(
            name_en,
            "Blue Widget",
            "the copy must not reuse the source product's English name verbatim",
        )
        self.assertIn("Blue Widget", name_en, "the English name keeps its own term")
        self.assertNotEqual(name_es, "Artilugio Azul")
        self.assertIn("Artilugio Azul", name_es, "the Spanish name keeps its own term")

    def test_duplicating_in_the_base_language_also_suffixes_translations(self):
        template = self._spanish_product()

        copy = template.with_context(lang="en_US").copy()
        self.env.flush_all()

        self.assertNotEqual(copy.with_context(lang="es_MX").name, "Artilugio Azul")
        self.assertIn("Artilugio Azul", copy.with_context(lang="es_MX").name)

    def test_renaming_a_copy_in_one_language_leaves_the_others_distinguishable(self):
        template = self._spanish_product()

        copy = template.with_context(lang="es_MX").copy()
        copy.with_context(lang="es_MX").name = "Artilugio Rojo"
        self.env.flush_all()

        self.assertEqual(copy.with_context(lang="es_MX").name, "Artilugio Rojo")
        self.assertNotEqual(copy.with_context(lang="en_US").name, "Blue Widget")

    def test_explicit_default_name_wins_in_every_language(self):
        template = self._spanish_product()

        copy = template.with_context(lang="es_MX").copy({"name": "Fixed Name"})
        self.env.flush_all()

        self.assertEqual(copy.with_context(lang="en_US").name, "Fixed Name")
        self.assertEqual(copy.with_context(lang="es_MX").name, "Fixed Name")

    def test_duplicating_a_variant_suffixes_every_language(self):
        template = self._spanish_product()

        variant = template.product_variant_id.with_context(lang="es_MX").copy()
        self.env.flush_all()

        self.assertNotEqual(variant.with_context(lang="en_US").name, "Blue Widget")
        self.assertIn("Blue Widget", variant.with_context(lang="en_US").name)
        self.assertIn("Artilugio Azul", variant.with_context(lang="es_MX").name)


@tagged("post_install", "-at_install")
class TestAttributeNameUniqueness(ProductCommon):
    @mute_logger("odoo.db.cursor")
    def test_duplicate_value_in_one_attribute_is_refused(self):
        attribute = self.env["product.attribute"].create({"name": "Fabric"})
        self.env["product.attribute.value"].create(
            {"name": "Denim", "attribute_id": attribute.id}
        )
        with self.assertRaises(psycopg.errors.UniqueViolation):
            with self.cr.savepoint():
                self.env["product.attribute.value"].create(
                    {"name": "Denim", "attribute_id": attribute.id}
                )

    def test_same_value_name_under_two_attributes_is_allowed(self):
        Attribute = self.env["product.attribute"]
        first = Attribute.create({"name": "Shirt Size"})
        second = Attribute.create({"name": "Shoe Size"})
        self.env["product.attribute.value"].create(
            [
                {"name": "Large", "attribute_id": first.id},
                {"name": "Large", "attribute_id": second.id},
            ]
        )
        self.env.flush_all()

    def test_duplicate_attribute_names_are_allowed(self):
        Attribute = self.env["product.attribute"]
        first = Attribute.create({"name": "Diameter"})
        second = Attribute.create({"name": "Diameter"})
        self.env.flush_all()
        self.assertNotEqual(first.id, second.id)

    def test_the_opt_out_stays_on_the_concrete_model(self):
        mixin = self.env.registry["mixin.attribute"]
        declared = [
            obj
            for cls in mixin._model_classes__
            for obj in getattr(cls, "_table_object_definitions", ())
            if obj.name == "name_src_uniq"
        ]
        self.assertFalse(
            [obj for obj in declared if obj.get_definition(self.env.registry) == ""],
            "mixin.attribute declares an opt-out; it belongs on the concrete model",
        )
