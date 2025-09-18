"""Comprehensive tests for product module code quality and performance fixes.

Tests are organized into sections:
- Bug fix verification (B1-B3)
- Performance optimization verification (P1-P14)
- Code quality fix verification (Q3-Q14)
- Coverage for untested models (product.document, product.category, etc.)
"""

from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase

from .common import ProductCommon, ProductVariantsCommon


class TestBugFixes(ProductCommon):
    """Verify all critical bug fixes remain fixed."""

    def test_b1_mutable_default_pricelist_recursion(self):
        """B1: _check_pricelist_recursion must not use mutable default argument.

        Previously, `seen=set()` was used as a default parameter, causing
        state leakage between calls. Verify independent calls don't share state.
        """
        self._enable_pricelists()
        pl_a = self._create_pricelist(name="PL A")
        pl_b = self._create_pricelist(name="PL B")

        # Create non-recursive chain: A → B (uses B as base)
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pl_a.id,
                "base": "pricelist",
                "base_pricelist_id": pl_b.id,
                "compute_price": "formula",
            }
        )

        # Now create a recursive chain: B → A (should be caught)
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
        """B1: Two separate non-recursive checks must not interfere."""
        self._enable_pricelists()
        pl_1 = self._create_pricelist(name="PL 1")
        pl_2 = self._create_pricelist(name="PL 2")
        pl_3 = self._create_pricelist(name="PL 3")
        pl_4 = self._create_pricelist(name="PL 4")

        # Chain 1: PL1 → PL2 (non-recursive)
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pl_1.id,
                "base": "pricelist",
                "base_pricelist_id": pl_2.id,
                "compute_price": "formula",
            }
        )
        # Chain 2: PL3 → PL4 (non-recursive, should NOT be affected by chain 1)
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pl_3.id,
                "base": "pricelist",
                "base_pricelist_id": pl_4.id,
                "compute_price": "formula",
            }
        )

    def test_b3_attribute_domain_boolean(self):
        """B3: Domain filter for product_tmpl_id.active must use boolean True, not string.

        The _compute_number_related_products and _compute_product_tmpl_ids methods
        must use boolean True in domain filters for the active field.
        """
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
        # The attribute should show it has related products
        attribute.invalidate_recordset(["number_related_products"])
        self.assertGreater(
            attribute.number_related_products,
            0,
            "Domain filter with boolean True should count active templates",
        )

        # Archive the template - count should drop
        template.active = False
        attribute.invalidate_recordset(["number_related_products"])
        self.assertEqual(
            attribute.number_related_products,
            0,
            "Archived templates should not be counted in number_related_products",
        )


class TestPerformanceOptimizations(ProductVariantsCommon):
    """Verify performance optimizations produce correct results."""

    def test_p1_batch_template_document_count(self):
        """P1: _compute_product_document_count on template should work in batch."""
        template1 = self.product.product_tmpl_id
        template2 = self.service_product.product_tmpl_id

        # Create documents for template1
        for i in range(3):
            self.env["product.document"].create(
                {
                    "name": f"Doc {i}",
                    "res_model": "product.template",
                    "res_id": template1.id,
                }
            )

        templates = template1 | template2
        templates.invalidate_recordset(["product_document_count"])
        self.assertEqual(template1.product_document_count, 3)
        self.assertEqual(template2.product_document_count, 0)

    def test_p2_batch_product_document_count(self):
        """P2: _compute_product_document_count on product should work in batch."""
        product1 = self.product
        product2 = self.service_product

        self.env["product.document"].create(
            {
                "name": "Variant Doc",
                "res_model": "product.product",
                "res_id": product1.id,
            }
        )

        products = product1 | product2
        products.invalidate_recordset(["product_document_count"])
        self.assertEqual(product1.product_document_count, 1)
        self.assertEqual(product2.product_document_count, 0)

    def test_p3_batch_set_template_field(self):
        """P3: _set_template_field batches variant count check via _read_group."""
        # Single-variant template: field should be set on template
        template = self.product.product_tmpl_id
        self.assertEqual(
            len(template.product_variant_ids),
            1,
            "Single variant expected",
        )

        # Set barcode on the single variant → should propagate to template
        self.product.barcode = "TEST123"
        self.assertEqual(template.barcode, "TEST123")

        # Multi-variant template: barcode should stay on variant
        sofa_red = self.product_sofa_red
        sofa_red.barcode = "SOFA-RED"
        self.assertEqual(sofa_red.barcode, "SOFA-RED")
        # Template barcode should not be set (multiple variants)
        self.assertFalse(self.product_template_sofa.barcode)

    def test_p5_category_product_count_hierarchical(self):
        """P5: Category product_count should work with hierarchical categories."""
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

        # Create products in each level
        self.env["product.template"].create(
            [
                {"name": "In Parent", "categ_id": parent_cat.id},
                {"name": "In Child 1", "categ_id": child_cat.id},
                {"name": "In Child 2", "categ_id": child_cat.id},
                {"name": "In Grandchild", "categ_id": grandchild_cat.id},
            ]
        )

        # Batch compute all at once
        categories = parent_cat | child_cat | grandchild_cat
        categories.invalidate_recordset(["product_count"])
        self.assertEqual(parent_cat.product_count, 4, "Parent should include all descendants")
        self.assertEqual(child_cat.product_count, 3, "Child should include grandchild")
        self.assertEqual(grandchild_cat.product_count, 1, "Grandchild has 1 product")

    def test_p6_get_filtered_sellers_batch(self):
        """P6: _get_filtered_sellers should not use O(N²) recordset concat."""
        partner1 = self.env["res.partner"].create({"name": "Vendor 1"})
        partner2 = self.env["res.partner"].create({"name": "Vendor 2"})

        template = self.product.product_tmpl_id
        self.env["product.supplierinfo"].create(
            [
                {"partner_id": partner1.id, "product_tmpl_id": template.id, "price": 10.0},
                {"partner_id": partner2.id, "product_tmpl_id": template.id, "price": 20.0},
            ]
        )

        sellers = self.product._get_filtered_sellers(partner_id=partner1)
        self.assertTrue(all(s.partner_id == partner1 for s in sellers))

    def test_p7_select_seller_batch(self):
        """P7: _select_seller should not use O(N²) recordset concat."""
        partner = self.env["res.partner"].create({"name": "Vendor"})
        template = self.product.product_tmpl_id

        self.env["product.supplierinfo"].create(
            [
                {"partner_id": partner.id, "product_tmpl_id": template.id, "price": 50.0, "min_qty": 1},
                {"partner_id": partner.id, "product_tmpl_id": template.id, "price": 40.0, "min_qty": 10},
            ]
        )

        seller = self.product._select_seller(partner_id=partner, quantity=5)
        self.assertEqual(seller.price, 50.0, "Should select seller matching quantity")

        seller_bulk = self.product._select_seller(partner_id=partner, quantity=15)
        self.assertEqual(seller_bulk.price, 40.0, "Should select bulk price seller")

    def test_p10_copy_no_quadratic(self):
        """P10: product.product copy() should use concat() instead of +=."""
        # Copy a single product (copy creates a new template)
        copy = self.product_sofa_red.copy()
        self.assertTrue(copy.exists())
        self.assertNotEqual(copy.product_tmpl_id, self.product_sofa_red.product_tmpl_id)
        # Copy returns a product.product recordset
        self.assertEqual(copy._name, "product.product")

    def test_p12_batch_pav_unlink(self):
        """P12: PAV unlink should batch PTAV search instead of per-record."""
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
        # Values not used on any product can be unlinked
        vals = attr.value_ids
        self.assertEqual(len(vals), 3)
        vals.unlink()
        self.assertFalse(vals.exists())


class TestCodeQualityFixes(ProductCommon):
    """Verify code quality improvements remain correct."""

    def test_q3_no_dead_compute_price_on_supplierinfo(self):
        """Q3: product.supplierinfo should not have a dead _compute_price method."""
        SupplierInfo = self.env["product.supplierinfo"]
        self.assertFalse(
            hasattr(SupplierInfo, "_compute_price")
            and callable(getattr(SupplierInfo, "_compute_price", None))
            and getattr(SupplierInfo._fields.get("price"), "compute", None) == "_compute_price",
            "price field should not reference a dead _compute_price method",
        )

    def test_q4_batch_combo_ids_clear(self):
        """Q4: Changing type from combo should clear combo_ids in batch."""
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

        # Change type from combo to consu → combo_ids should be cleared
        template.type = "consu"
        self.assertFalse(template.combo_ids)

    def test_q9_supplierinfo_context_get(self):
        """Q9: _compute_product_id should use self.env.context.get, not self.env.get."""
        partner = self.env["res.partner"].create({"name": "Supplier"})
        template = self.product.product_tmpl_id

        # Create supplierinfo with context default_product_id
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
        """Q11: _get_default_pricelist_vals should return correct structure."""
        company = self.env.company
        vals = company._get_default_pricelist_vals()
        self.assertIn("name", vals)
        self.assertIn("currency_id", vals)
        self.assertIn("company_id", vals)
        self.assertEqual(vals["company_id"], company.id)
        self.assertEqual(vals["currency_id"], company.currency_id.id)

    def test_q14_check_date_range_constraint(self):
        """Q14: _check_date_range should raise on invalid date range (no dead return)."""
        self._enable_pricelists()
        with self.assertRaises(ValidationError, msg="Date range constraint not enforced"):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": self.pricelist.id,
                    "date_start": fields.Datetime.now(),
                    "date_end": fields.Datetime.now() - timedelta(days=1),
                    "compute_price": "fixed",
                    "fixed_price": 10.0,
                }
            )


class TestProductDocument(ProductCommon):
    """Tests for product.document model (previously zero coverage)."""

    def test_create_document(self):
        """Create product documents and verify linkage."""
        doc = self.env["product.document"].create(
            {
                "name": "Test Document",
                "res_model": "product.template",
                "res_id": self.product.product_tmpl_id.id,
            }
        )
        self.assertTrue(doc.ir_attachment_id)
        self.assertEqual(doc.res_model, "product.template")

    def test_document_unlink_cascades_attachment(self):
        """Unlinking a document should also remove the underlying attachment."""
        doc = self.env["product.document"].create(
            {
                "name": "To Delete",
                "res_model": "product.template",
                "res_id": self.product.product_tmpl_id.id,
            }
        )
        attachment_id = doc.ir_attachment_id.id
        doc.unlink()
        self.assertFalse(
            self.env["ir.attachment"].browse(attachment_id).exists(),
            "Attachment should be deleted when document is deleted",
        )

    def test_document_copy(self):
        """Copying a document should copy the underlying attachment too."""
        doc = self.env["product.document"].create(
            {
                "name": "Original",
                "res_model": "product.template",
                "res_id": self.product.product_tmpl_id.id,
            }
        )
        copy = doc.copy()
        self.assertNotEqual(copy.ir_attachment_id, doc.ir_attachment_id)


class TestProductCategory(ProductCommon):
    """Tests for product.category (previously minimal coverage)."""

    def test_complete_name_hierarchy(self):
        """Complete name should include full hierarchy path."""
        parent = self.env["product.category"].create({"name": "Electronics"})
        child = self.env["product.category"].create(
            {
                "name": "Phones",
                "parent_id": parent.id,
            }
        )
        self.assertEqual(child.complete_name, "Electronics / Phones")

    def test_category_recursion_constraint(self):
        """Cannot create circular category hierarchy."""
        cat_a = self.env["product.category"].create({"name": "A"})
        cat_b = self.env["product.category"].create(
            {
                "name": "B",
                "parent_id": cat_a.id,
            }
        )
        # _parent_store_update raises UserError; _check_category_recursion raises ValidationError
        with self.assertRaises(UserError):
            cat_a.parent_id = cat_b.id

    def test_category_copy_appends_copy(self):
        """Copying a category should append (copy) to name."""
        cat = self.env["product.category"].create({"name": "Original"})
        copy = cat.copy()
        self.assertIn("(copy)", copy.name)

    def test_display_name_flat(self):
        """With hierarchical_naming=False, display_name should be just name."""
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
        """name_create should create a category and return (id, display_name)."""
        result = self.env["product.category"].name_create("New Category")
        self.assertEqual(result[1], "New Category")


class TestPricelistItemConstraints(ProductCommon):
    """Tests for pricelist item constraints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._enable_pricelists()

    def test_margin_constraint(self):
        """Min margin must be lower than max margin."""
        with self.assertRaises(ValidationError):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": self.pricelist.id,
                    "compute_price": "formula",
                    "price_min_margin": 50.0,
                    "price_max_margin": 10.0,
                }
            )

    def test_product_consistency_constraint(self):
        """applied_on requires corresponding product/category fields to be set."""
        # applied_on="1_product" without product_tmpl_id should raise
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
        """Three-level pricelist chain should be detected: A → B → C → A."""
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
    """Tests for product.supplierinfo compute methods."""

    def test_compute_product_uom_id(self):
        """UOM should default from product or template."""
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
        """Discounted price should apply discount percentage."""
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

    def test_sanitize_vals_sets_template(self):
        """Creating supplierinfo with product_id should auto-set product_tmpl_id."""
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
    """Tests for res.company pricelist auto-creation."""

    def test_company_creates_default_pricelist(self):
        """Creating a company should auto-create a default pricelist."""
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
        self.assertTrue(pricelist, "Default pricelist should be created for new company")


class TestVariantOptimizations(ProductVariantsCommon):
    """Verify variant-related optimizations work correctly."""

    def test_p8_variant_limit_hoisted(self):
        """P8: variant_limit config param should work (hoisted before loop)."""
        # Create a template that would exceed a low limit
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
        """P14: Combo items should be batch-cleaned when variants are unlinked."""
        # Create combo product referencing a variant
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

        # Remove the color attribute → variants get recreated, combo items cleaned
        self.product_template_sofa.write(
            {
                "attribute_line_ids": [(2, self.product_template_sofa.attribute_line_ids.id)],
            }
        )
        # The old variant is gone, combo item should be cleaned up
        combo_choice.invalidate_recordset()
        self.assertFalse(
            combo_choice.combo_item_ids.filtered(lambda ci: ci.product_id == self.product_sofa_red),
            "Combo items referencing deleted variants should be cleaned up",
        )
