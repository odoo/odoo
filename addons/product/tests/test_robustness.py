from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase

from .common import ProductCommon, ProductVariantsCommon


class TestBugFixes(ProductCommon):
    def test_b1_mutable_default_pricelist_recursion(self):
        self._enable_pricelists()
        pl_a = self._create_pricelist(name="PL A")
        pl_b = self._create_pricelist(name="PL B")

        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pl_a.id,
                "base": "pricelist",
                "base_pricelist_id": pl_b.id,
                "compute_price": "formula",
            }
        )

        with self.assertRaises(ValidationError, msg="Recursive pricelist not detected"):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": pl_b.id,
                    "base": "pricelist",
                    "base_pricelist_id": pl_a.id,
                    "compute_price": "formula",
                }
            )

    def test_b1_pricelist_recursion_independent_checks(self):
        self._enable_pricelists()
        pl_1 = self._create_pricelist(name="PL 1")
        pl_2 = self._create_pricelist(name="PL 2")
        pl_3 = self._create_pricelist(name="PL 3")
        pl_4 = self._create_pricelist(name="PL 4")

        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pl_1.id,
                "base": "pricelist",
                "base_pricelist_id": pl_2.id,
                "compute_price": "formula",
            }
        )
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pl_3.id,
                "base": "pricelist",
                "base_pricelist_id": pl_4.id,
                "compute_price": "formula",
            }
        )

    def test_b3_attribute_domain_boolean(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "Test Attr B3",
                "value_ids": [Command.create({"name": "V1"})],
            }
        )
        template = self.env["product.template"].create(
            {
                "name": "B3 Product",
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
        attribute.invalidate_recordset(["count_product_tmpl"])
        self.assertGreater(
            attribute.count_product_tmpl,
            0,
            "Domain filter with boolean True should count active templates",
        )

        template.active = False
        attribute.invalidate_recordset(["count_product_tmpl"])
        self.assertEqual(
            attribute.count_product_tmpl,
            0,
            "Archived templates should not be counted in count_product_tmpl",
        )


class TestPerformanceOptimizations(ProductVariantsCommon):
    def test_p3_batch_set_template_field(self):
        template = self.product.product_tmpl_id
        self.assertEqual(
            len(template.product_variant_ids),
            1,
            "Single variant expected",
        )

        self.product.barcode = "TEST123"
        self.assertEqual(template.barcode, "TEST123")

        sofa_red = self.product_sofa_red
        sofa_red.barcode = "SOFA-RED"
        self.assertEqual(sofa_red.barcode, "SOFA-RED")
        self.assertFalse(self.product_template_sofa.barcode)

    def test_p5_category_product_count_hierarchical(self):
        parent_cat = self.env["product.category"].create({"name": "Parent"})
        child_cat = self.env["product.category"].create(
            {
                "name": "Child",
                "parent_id": parent_cat.id,
            }
        )
        grandchild_cat = self.env["product.category"].create(
            {
                "name": "Grandchild",
                "parent_id": child_cat.id,
            }
        )

        self.env["product.template"].create(
            [
                {"name": "In Parent", "categ_id": parent_cat.id},
                {"name": "In Child 1", "categ_id": child_cat.id},
                {"name": "In Child 2", "categ_id": child_cat.id},
                {"name": "In Grandchild", "categ_id": grandchild_cat.id},
            ]
        )

        categories = parent_cat | child_cat | grandchild_cat
        categories.invalidate_recordset(["product_count"])
        self.assertEqual(
            parent_cat.product_count, 4, "Parent should include all descendants"
        )
        self.assertEqual(child_cat.product_count, 3, "Child should include grandchild")
        self.assertEqual(grandchild_cat.product_count, 1, "Grandchild has 1 product")

    def test_p6_get_filtered_sellers_batch(self):
        partner1 = self.env["res.partner"].create({"name": "Vendor 1"})
        partner2 = self.env["res.partner"].create({"name": "Vendor 2"})

        template = self.product.product_tmpl_id
        self.env["product.supplierinfo"].create(
            [
                {
                    "partner_id": partner1.id,
                    "product_tmpl_id": template.id,
                    "price": 10.0,
                },
                {
                    "partner_id": partner2.id,
                    "product_tmpl_id": template.id,
                    "price": 20.0,
                },
            ]
        )

        sellers = self.product._get_filtered_sellers(partner_id=partner1)
        self.assertTrue(all(s.partner_id == partner1 for s in sellers))

    def test_p7_select_seller_batch(self):
        partner = self.env["res.partner"].create({"name": "Vendor"})
        template = self.product.product_tmpl_id

        self.env["product.supplierinfo"].create(
            [
                {
                    "partner_id": partner.id,
                    "product_tmpl_id": template.id,
                    "price": 50.0,
                    "min_qty": 1,
                },
                {
                    "partner_id": partner.id,
                    "product_tmpl_id": template.id,
                    "price": 40.0,
                    "min_qty": 10,
                },
            ]
        )

        seller = self.product._select_seller(partner_id=partner, quantity=5)
        self.assertEqual(seller.price, 50.0, "Should select seller matching quantity")

        seller_bulk = self.product._select_seller(partner_id=partner, quantity=15)
        self.assertEqual(seller_bulk.price, 40.0, "Should select bulk price seller")

    def test_p10_copy_no_quadratic(self):
        copy = self.product_sofa_red.copy()
        self.assertTrue(copy.exists())
        self.assertNotEqual(copy.product_tmpl_id, self.product_sofa_red.product_tmpl_id)
        self.assertEqual(copy._name, "product.product")

    def test_p12_batch_pav_unlink(self):
        attr = self.env["product.attribute"].create(
            {
                "name": "Batch Test",
                "value_ids": [
                    Command.create({"name": "Val A"}),
                    Command.create({"name": "Val B"}),
                    Command.create({"name": "Val C"}),
                ],
            }
        )
        vals = attr.value_ids
        self.assertEqual(len(vals), 3)
        vals.unlink()
        self.assertFalse(vals.exists())


class TestCodeQualityFixes(ProductCommon):
    def test_q3_no_dead_compute_price_on_supplierinfo(self):
        SupplierInfo = self.env["product.supplierinfo"]
        self.assertFalse(
            hasattr(SupplierInfo, "_compute_price")
            and callable(getattr(SupplierInfo, "_compute_price", None))
            and getattr(SupplierInfo._fields.get("price"), "compute", None)
            == "_compute_price",
            "price field should not reference a dead _compute_price method",
        )

    def test_q4_batch_combo_ids_clear(self):
        combo_choice = self.env["product.combo"].create(
            {
                "name": "Choice",
                "combo_item_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                        }
                    )
                ],
            }
        )
        template = self.env["product.template"].create(
            {
                "name": "Combo Product",
                "type": "combo",
                "combo_ids": [Command.link(combo_choice.id)],
            }
        )
        self.assertTrue(template.combo_ids)

        template.type = "consu"
        self.assertFalse(template.combo_ids)

    def test_q9_supplierinfo_context_get(self):
        partner = self.env["res.partner"].create({"name": "Supplier"})
        template = self.product.product_tmpl_id

        supplier = (
            self.env["product.supplierinfo"]
            .with_context(
                default_product_id=self.product.id,
            )
            .create(
                {
                    "partner_id": partner.id,
                    "product_tmpl_id": template.id,
                    "price": 15.0,
                }
            )
        )
        self.assertEqual(
            supplier.product_id,
            self.product,
            "Context default_product_id should be applied",
        )

    def test_q11_simplified_pricelist_vals(self):
        company = self.env.company
        vals = company._prepare_default_pricelist_vals()
        self.assertIn("name", vals)
        self.assertIn("currency_id", vals)
        self.assertIn("company_id", vals)
        self.assertEqual(vals["company_id"], company.id)
        self.assertEqual(vals["currency_id"], company.currency_id.id)

    def test_q14_check_date_range_constraint(self):
        self._enable_pricelists()
        with self.assertRaises(
            ValidationError, msg="Date range constraint not enforced"
        ):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": self.pricelist.id,
                    "date_start": fields.Datetime.now(),
                    "date_end": fields.Datetime.now() - timedelta(days=1),
                    "compute_price": "fixed",
                    "fixed_price": 10.0,
                }
            )


class TestProductCategory(ProductCommon):
    def test_complete_name_hierarchy(self):
        parent = self.env["product.category"].create({"name": "Electronics"})
        child = self.env["product.category"].create(
            {
                "name": "Phones",
                "parent_id": parent.id,
            }
        )
        self.assertEqual(child.complete_name, "Electronics / Phones")

    def test_category_recursion_constraint(self):
        cat_a = self.env["product.category"].create({"name": "A"})
        cat_b = self.env["product.category"].create(
            {
                "name": "B",
                "parent_id": cat_a.id,
            }
        )
        with self.assertRaises(UserError):
            cat_a.parent_id = cat_b.id

    def test_category_copy_appends_copy(self):
        cat = self.env["product.category"].create({"name": "Original"})
        copy = cat.copy()
        self.assertIn("(copy)", copy.name)

    def test_display_name_flat(self):
        parent = self.env["product.category"].create({"name": "Parent"})
        child = self.env["product.category"].create(
            {
                "name": "Child",
                "parent_id": parent.id,
            }
        )
        self.assertEqual(child.complete_name, "Parent / Child")
        flat_child = child.with_context(hierarchical_naming=False)
        self.assertEqual(flat_child.display_name, "Child")

    def test_name_create(self):
        result = self.env["product.category"].name_create("New Category")
        self.assertEqual(result[1], "New Category")


class TestPricelistItemConstraints(ProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._enable_pricelists()

    def test_margin_constraint(self):
        with self.assertRaises(ValidationError):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": self.pricelist.id,
                    "compute_price": "formula",
                    "price_min_margin": 50.0,
                    "price_max_margin": 10.0,
                }
            )

    def test_margin_zero_max_is_uncapped(self):
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "compute_price": "formula",
                "price_min_margin": 5.0,
                "price_max_margin": 0.0,
            }
        )
        self.assertTrue(rule.exists())

    def test_price_round_negative_constraint(self):
        with self.assertRaises(ValidationError):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": self.pricelist.id,
                    "compute_price": "formula",
                    "price_round": -1.0,
                }
            )

    def test_product_consistency_constraint(self):
        with self.assertRaises(ValidationError):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": self.pricelist.id,
                    "applied_on": "1_product",
                    "product_tmpl_id": False,
                    "compute_price": "fixed",
                    "fixed_price": 5.0,
                }
            )

    def test_three_level_pricelist_recursion(self):
        pl_a = self._create_pricelist(name="PL A")
        pl_b = self._create_pricelist(name="PL B")
        pl_c = self._create_pricelist(name="PL C")

        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pl_a.id,
                "base": "pricelist",
                "base_pricelist_id": pl_b.id,
                "compute_price": "formula",
            }
        )
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pl_b.id,
                "base": "pricelist",
                "base_pricelist_id": pl_c.id,
                "compute_price": "formula",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": pl_c.id,
                    "base": "pricelist",
                    "base_pricelist_id": pl_a.id,
                    "compute_price": "formula",
                }
            )


class TestSupplierInfoCompute(ProductCommon):
    def test_compute_product_uom_id(self):
        partner = self.env["res.partner"].create({"name": "Vendor"})
        supplier = self.env["product.supplierinfo"].create(
            {
                "partner_id": partner.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "price": 10.0,
            }
        )
        self.assertEqual(
            supplier.product_uom_id,
            self.product.product_tmpl_id.uom_id,
            "UOM should default from template",
        )

    def test_compute_price_discounted(self):
        partner = self.env["res.partner"].create({"name": "Vendor"})
        supplier = self.env["product.supplierinfo"].create(
            {
                "partner_id": partner.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "price": 100.0,
                "discount": 10.0,
            }
        )
        self.assertAlmostEqual(
            supplier.price_discounted,
            90.0,
            places=2,
            msg="10% discount on 100 should be 90",
        )

    def test_normalize_vals_sets_template(self):
        partner = self.env["res.partner"].create({"name": "Vendor"})
        supplier = self.env["product.supplierinfo"].create(
            {
                "partner_id": partner.id,
                "product_id": self.product.id,
                "price": 10.0,
            }
        )
        self.assertEqual(
            supplier.product_tmpl_id,
            self.product.product_tmpl_id,
            "product_tmpl_id should be auto-set from product_id",
        )


class TestResCompanyPricelist(TransactionCase):
    def test_company_creates_default_pricelist(self):
        self.env.user.group_ids += self.env.ref("product.group_product_pricelist")
        company = self.env["res.company"].create(
            {
                "name": "Test Company PL",
            }
        )
        pricelist = self.env["product.pricelist"].search(
            [
                ("company_id", "=", company.id),
            ]
        )
        self.assertTrue(
            pricelist, "Default pricelist should be created for new company"
        )


class TestVariantOptimizations(ProductVariantsCommon):
    def test_p8_variant_limit_hoisted(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "product.dynamic_variant_limit",
            "2",
        )
        attr = self.env["product.attribute"].create(
            {
                "name": "Many Values",
                "value_ids": [Command.create({"name": f"V{i}"}) for i in range(4)],
            }
        )
        with self.assertRaises(UserError, msg="Variant limit should be enforced"):
            self.env["product.template"].create(
                {
                    "name": "Too Many Variants",
                    "attribute_line_ids": [
                        Command.create(
                            {
                                "attribute_id": attr.id,
                                "value_ids": [Command.set(attr.value_ids.ids)],
                            }
                        )
                    ],
                }
            )

    def test_p14_batch_combo_items_cleanup(self):
        combo_choice = self.env["product.combo"].create(
            {
                "name": "Sofa Choice",
                "combo_item_ids": [
                    Command.create(
                        {
                            "product_id": self.product_sofa_red.id,
                        }
                    )
                ],
            }
        )
        self.assertEqual(len(combo_choice.combo_item_ids), 1)

        self.product_template_sofa.write(
            {
                "attribute_line_ids": [
                    (2, self.product_template_sofa.attribute_line_ids.id)
                ],
            }
        )
        combo_choice.invalidate_recordset()
        self.assertFalse(
            combo_choice.combo_item_ids.filtered(
                lambda ci: ci.product_id == self.product_sofa_red
            ),
            "Combo items referencing deleted variants should be cleaned up",
        )


class TestPricelistItemComputeHardening(ProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._enable_pricelists()

    def test_percentage_compute_price(self):
        product = self._create_product(list_price=200.0)
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "3_global",
                "compute_price": "percentage",
                "percent_price": 25.0,
            }
        )
        price = rule._get_price(
            product, 1.0, product.uom_id, date=fields.Datetime.now()
        )
        self.assertAlmostEqual(price, 150.0, places=2)

    def test_name_recomputes_on_display_applied_on_change(self):
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "3_global",
                "display_applied_on": "1_product",
                "compute_price": "fixed",
                "fixed_price": 1.0,
            }
        )
        self.assertEqual(rule.name, "All Products")
        rule.display_applied_on = "2_product_category"
        self.assertEqual(rule.name, "All Categories")

    def test_rule_amounts_expressed_in_requested_currency(self):
        company = self.env.company
        rule_cur = company.currency_id
        req_cur = self.env.ref("base.EUR")
        if req_cur == rule_cur:
            req_cur = self.env.ref("base.USD")
        req_cur.active = True
        date = datetime(2099, 1, 1)
        self.env["res.currency.rate"].create(
            {
                "currency_id": req_cur.id,
                "name": "2099-01-01",
                "rate": 2.0,
                "company_id": company.id,
            }
        )
        pricelist = self._create_pricelist(currency_id=rule_cur.id)
        product = self._create_product(list_price=100.0)

        fixed_rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pricelist.id,
                "applied_on": "3_global",
                "compute_price": "fixed",
                "fixed_price": 50.0,
            }
        )
        got = fixed_rule._get_price(
            product, 1.0, product.uom_id, date=date, currency=req_cur
        )
        self.assertAlmostEqual(
            got, rule_cur._convert(50.0, req_cur, company, date), places=2
        )
        self.assertAlmostEqual(got, 100.0, places=2)

        surcharge_rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pricelist.id,
                "applied_on": "3_global",
                "compute_price": "formula",
                "base": "list_price",
                "price_discount": 0.0,
                "price_surcharge": 10.0,
            }
        )
        got2 = surcharge_rule._get_price(
            product, 1.0, product.uom_id, date=date, currency=req_cur
        )
        base_req = rule_cur._convert(100.0, req_cur, company, date)
        surcharge_req = rule_cur._convert(10.0, req_cur, company, date)
        self.assertAlmostEqual(got2, base_req + surcharge_req, places=2)


class TestPricelistItemRefactor(ProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._enable_pricelists()

    def _second_currency(self, rate):
        company = self.env.company
        rule_cur = company.currency_id
        req = self.env.ref("base.EUR")
        if req == rule_cur:
            req = self.env.ref("base.USD")
        req.active = True
        self.env["res.currency.rate"].search([("currency_id", "=", req.id)]).unlink()
        self.env["res.currency.rate"].create(
            {
                "currency_id": req.id,
                "name": "2099-01-01",
                "rate": rate,
                "company_id": company.id,
            }
        )
        return rule_cur, req

    def test_price_round_is_currency_consistent(self):
        rule_cur, req = self._second_currency(3.0)
        date = datetime(2099, 1, 1)
        pricelist = self._create_pricelist(currency_id=rule_cur.id)
        product = self._create_product(list_price=33.0)
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pricelist.id,
                "applied_on": "3_global",
                "compute_price": "formula",
                "base": "list_price",
                "price_discount": 0.0,
                "price_round": 10.0,
            }
        )
        same = rule._get_price(
            product, 1.0, product.uom_id, date=date, currency=rule_cur
        )
        self.assertAlmostEqual(same, 30.0, places=2, msg="same-currency grid of 10")
        cross = rule._get_price(product, 1.0, product.uom_id, date=date, currency=req)
        self.assertAlmostEqual(
            cross, 90.0, places=2, msg="cross-currency grid must convert to 30"
        )

    def test_price_markup_not_stored_but_inverts(self):
        PI = self.env["product.pricelist.item"]
        self.assertFalse(
            PI._fields["price_markup"].store,
            "price_markup should not be stored (pure negation of price_discount)",
        )
        rule = PI.create(
            {
                "pricelist_id": self.pricelist.id,
                "compute_price": "formula",
                "base": "standard_price",
                "price_discount": 15.0,
            }
        )
        self.assertEqual(rule.price_markup, -15.0)
        rule.price_markup = 40.0
        rule.invalidate_recordset()
        self.assertEqual(rule.price_discount, -40.0)
        self.assertEqual(rule.price_markup, 40.0)

    def test_create_batches_variant_template_deduction(self):
        products = self.env["product.product"].create(
            [{"name": "BV1"}, {"name": "BV2"}, {"name": "BV3"}]
        )
        rules = self.env["product.pricelist.item"].create(
            [
                {
                    "pricelist_id": self.pricelist.id,
                    "product_id": p.id,
                    "compute_price": "fixed",
                    "fixed_price": 1.0,
                }
                for p in products
            ]
        )
        for rule, product in zip(rules, products, strict=True):
            self.assertEqual(rule.product_tmpl_id, product.product_tmpl_id)
            self.assertEqual(rule.applied_on, "0_product_variant")

    def test_deduce_applied_on_precedence(self):
        PI = self.env["product.pricelist.item"]
        self.assertEqual(
            PI._deduce_applied_on(product_id=1, product_tmpl_id=2, categ_id=3),
            "0_product_variant",
        )
        self.assertEqual(
            PI._deduce_applied_on(product_tmpl_id=2, categ_id=3), "1_product"
        )
        self.assertEqual(PI._deduce_applied_on(categ_id=3), "2_product_category")
        self.assertEqual(PI._deduce_applied_on(), "3_global")

    def test_is_applicable_for_category_descendant(self):
        parent = self.env["product.category"].create({"name": "RP"})
        child = self.env["product.category"].create(
            {"name": "RC", "parent_id": parent.id}
        )
        other = self.env["product.category"].create({"name": "RO"})
        in_child = self._create_product(categ_id=child.id)
        in_other = self._create_product(categ_id=other.id)
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "2_product_category",
                "categ_id": parent.id,
                "compute_price": "fixed",
                "fixed_price": 1.0,
            }
        )
        self.assertTrue(rule._is_applicable_for(in_child, 1.0))
        self.assertFalse(rule._is_applicable_for(in_other, 1.0))

    def test_is_applicable_for_min_quantity(self):
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "3_global",
                "min_quantity": 5.0,
                "compute_price": "fixed",
                "fixed_price": 1.0,
            }
        )
        product = self._create_product()
        self.assertFalse(rule._is_applicable_for(product, 4.0))
        self.assertTrue(rule._is_applicable_for(product, 5.0))

    def test_is_applicable_for_single_variant_template(self):
        product = self._create_product()
        template = product.product_tmpl_id
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "0_product_variant",
                "product_id": product.id,
                "compute_price": "fixed",
                "fixed_price": 1.0,
            }
        )
        self.assertTrue(rule._is_applicable_for(template, 1.0))
        self.assertTrue(rule._is_applicable_for(product, 1.0))
