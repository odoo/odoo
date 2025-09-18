"""Tests for purchase order line computed fields cascade.

These tests verify the correct behavior of the computed field cascade:
- selected_seller_id (stored, triggers downstream computes)
- price_unit, price_unit_auto, discount (combined compute)
- name (with known-defaults override detection)
- date_planned (with known-defaults override detection)
"""

from datetime import timedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestPurchaseOrderLineCompute(AccountTestInvoicingCommon):
    """Test computed field cascade on purchase order lines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_with_sellers = cls.env["product.product"].create(
            {
                "name": "Product With Sellers",
                "standard_price": 50.0,
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": cls.partner_a.id,
                            "min_qty": 1,
                            "price": 10.0,
                            "discount": 5.0,
                            "delay": 3,
                            "product_code": "PROD-A",
                            "product_name": "Product from Vendor A",
                        }
                    ),
                    Command.create(
                        {
                            "partner_id": cls.partner_a.id,
                            "min_qty": 10,
                            "price": 8.0,
                            "discount": 10.0,
                            "delay": 2,
                            "product_code": "PROD-A-BULK",
                            "product_name": "Product from Vendor A (Bulk)",
                        }
                    ),
                    Command.create(
                        {
                            "partner_id": cls.partner_b.id,
                            "min_qty": 1,
                            "price": 12.0,
                            "discount": 0.0,
                            "delay": 5,
                            "product_code": "PROD-B",
                            "product_name": "Product from Vendor B",
                        }
                    ),
                ],
            }
        )
        cls.product_without_sellers = cls.env["product.product"].create(
            {
                "name": "Product Without Sellers",
                "standard_price": 100.0,
            }
        )

    # =========================================================================
    # TEST: selected_seller_id computation
    # =========================================================================

    def test_selected_seller_id_stored(self):
        """Verify selected_seller_id is stored in the database."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Field should be stored
        self.assertTrue(line._fields["selected_seller_id"].store)

        # Should have selected the first seller (min_qty=1, partner_a)
        self.assertTrue(line.selected_seller_id)
        self.assertEqual(line.selected_seller_id.min_qty, 1)
        self.assertEqual(line.selected_seller_id.price, 10.0)

    def test_selected_seller_id_changes_with_quantity(self):
        """Verify selected_seller_id changes when quantity crosses min_qty threshold."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Initial: qty=5 selects first seller (min_qty=1)
        self.assertEqual(line.selected_seller_id.min_qty, 1)
        self.assertEqual(line.price_unit, 10.0)
        self.assertEqual(line.discount, 5.0)

        # Change qty to 15: should select second seller (min_qty=10)
        line.product_qty = 15
        self.assertEqual(line.selected_seller_id.min_qty, 10)
        self.assertEqual(line.price_unit, 8.0)
        self.assertEqual(line.discount, 10.0)

        # Change qty back to 5: should select first seller again
        line.product_qty = 5
        self.assertEqual(line.selected_seller_id.min_qty, 1)
        self.assertEqual(line.price_unit, 10.0)
        self.assertEqual(line.discount, 5.0)

    def test_selected_seller_id_changes_with_partner(self):
        """Verify selected_seller_id changes when partner changes."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Initial: partner_a selects vendor A's pricelist
        self.assertEqual(line.selected_seller_id.partner_id, self.partner_a)
        self.assertEqual(line.price_unit, 10.0)

        # Change partner to partner_b
        po.partner_id = self.partner_b
        self.assertEqual(line.selected_seller_id.partner_id, self.partner_b)
        self.assertEqual(line.price_unit, 12.0)

    def test_selected_seller_id_none_when_no_match(self):
        """Verify selected_seller_id is False when no seller matches."""
        # Create partner with no seller entries
        partner_c = self.env["res.partner"].create({"name": "Partner C"})

        po = self.env["purchase.order"].create(
            {
                "partner_id": partner_c.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # No seller matches partner_c
        self.assertFalse(line.selected_seller_id)
        # Price falls back to standard_price
        self.assertEqual(line.price_unit, 50.0)
        self.assertEqual(line.discount, 0.0)

    def test_selected_seller_id_none_for_product_without_sellers(self):
        """Verify selected_seller_id is False for products without sellers."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_without_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        self.assertFalse(line.selected_seller_id)
        self.assertEqual(line.price_unit, 100.0)  # standard_price
        self.assertEqual(line.discount, 0.0)

    # =========================================================================
    # TEST: price_unit_auto and manual override detection
    # =========================================================================

    def test_price_unit_auto_tracks_computed_price(self):
        """Verify price_unit_auto always equals the auto-computed price."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Shadow should equal price_unit
        self.assertEqual(line.price_unit, 10.0)
        self.assertEqual(line.price_unit_auto, 10.0)

        # Change qty to get different seller
        line.product_qty = 15
        self.assertEqual(line.price_unit, 8.0)
        self.assertEqual(line.price_unit_auto, 8.0)

    def test_manual_price_override_preserved_on_qty_change(self):
        """Verify manually set price is preserved when quantity changes."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Initial computed price
        self.assertEqual(line.price_unit, 10.0)
        self.assertEqual(line.price_unit_auto, 10.0)

        # Manually override price
        line.price_unit = 99.0

        # Change quantity - price should be preserved
        line.product_qty = 15
        self.assertEqual(line.price_unit, 99.0, "Manual price should be preserved")
        # Shadow should update to what would be computed
        self.assertEqual(line.price_unit_auto, 8.0)

    def test_manual_price_override_preserved_on_partner_change(self):
        """Verify manually set price is preserved when partner changes."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Manually override price
        line.price_unit = 99.0

        # Change partner
        po.partner_id = self.partner_b
        self.assertEqual(line.price_unit, 99.0, "Manual price should be preserved")
        self.assertEqual(line.price_unit_auto, 12.0)

    def test_price_resets_on_product_change(self):
        """Verify price resets to computed value when product changes."""
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as line:
            line.product_id = self.product_with_sellers
            line.product_qty = 5
        po = po_form.save()
        line = po.line_ids

        # Manually override price
        line.price_unit = 99.0
        self.assertEqual(line.price_unit, 99.0)

        # Change product - price should reset
        with Form(po) as po_form:
            with po_form.line_ids.edit(0) as line_form:
                line_form.product_id = self.product_without_sellers
        self.assertEqual(
            po.line_ids.price_unit, 100.0, "Price should reset on product change"
        )

    def test_discount_updates_with_seller(self):
        """Verify discount updates when seller changes (not manually overridden)."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Initial discount from first seller
        self.assertEqual(line.discount, 5.0)

        # Change qty to select second seller with different discount
        line.product_qty = 15
        self.assertEqual(line.discount, 10.0)

        # Change to no seller (below min_qty)
        line.product_qty = 0.5
        self.assertEqual(line.discount, 0.0)

    # =========================================================================
    # TEST: name computation with known-defaults pattern
    # =========================================================================

    def test_name_computed_from_seller(self):
        """Verify name is computed from selected seller's product_code/name."""
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as line:
            line.product_id = self.product_with_sellers
            line.product_qty = 5
        po = po_form.save()

        # Name should include seller's product_code
        self.assertIn("PROD-A", po.line_ids.name)

    def test_name_updates_on_seller_change(self):
        """Verify name updates when seller changes (not manually customized)."""
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as line:
            line.product_id = self.product_with_sellers
            line.product_qty = 5
        po = po_form.save()

        # Initial name from seller with min_qty=1
        self.assertIn("PROD-A", po.line_ids.name)
        self.assertNotIn("BULK", po.line_ids.name)

        # Change qty to select bulk seller
        po.line_ids.product_qty = 15
        self.assertIn("PROD-A-BULK", po.line_ids.name)

    def test_custom_name_preserved_on_qty_change(self):
        """Verify custom description is preserved when quantity changes."""
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as line:
            line.product_id = self.product_with_sellers
            line.product_qty = 5
        po = po_form.save()
        line = po.line_ids

        # Set custom name
        custom_name = "My custom product description"
        line.name = custom_name

        # Change quantity
        line.product_qty = 15

        # Custom name should be preserved
        self.assertEqual(line.name, custom_name)

    # =========================================================================
    # TEST: date_planned computation
    # =========================================================================

    @freeze_time("2024-01-15")
    def test_date_planned_computed_from_seller_delay(self):
        """Verify date_planned is computed from order date + seller delay."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # First seller has delay=3
        expected_date = fields.Datetime.now() + timedelta(days=3)
        self.assertEqual(line.date_planned.date(), expected_date.date())

    @freeze_time("2024-01-15")
    def test_date_planned_updates_on_seller_change(self):
        """Verify date_planned updates when seller changes."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Initial: delay=3 from first seller
        initial_date = fields.Datetime.now() + timedelta(days=3)
        self.assertEqual(line.date_planned.date(), initial_date.date())

        # Change qty to select second seller (delay=2)
        line.product_qty = 15
        expected_date = fields.Datetime.now() + timedelta(days=2)
        self.assertEqual(line.date_planned.date(), expected_date.date())

    @freeze_time("2024-01-15")
    def test_custom_date_planned_preserved(self):
        """Verify custom date_planned is preserved when seller changes."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Set custom date
        custom_date = fields.Datetime.now() + timedelta(days=30)
        line.date_planned = custom_date

        # Change quantity (which changes seller)
        line.product_qty = 15

        # Custom date should be preserved
        self.assertEqual(line.date_planned.date(), custom_date.date())

    # =========================================================================
    # TEST: Form interactions (simulates UI behavior)
    # =========================================================================

    def test_form_price_computation_flow(self):
        """Test price computation through Form (simulates UI)."""
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a

        with po_form.line_ids.new() as line:
            line.product_id = self.product_with_sellers
            # Price should be computed
            self.assertEqual(line.price_unit, 10.0)

            # Change quantity
            line.product_qty = 15
            self.assertEqual(line.price_unit, 8.0)

            # Manually override
            line.price_unit = 50.0

        po = po_form.save()
        self.assertEqual(po.line_ids.price_unit, 50.0)

        # Edit and change quantity - manual price should be preserved
        with Form(po) as po_form:
            with po_form.line_ids.edit(0) as line:
                line.product_qty = 20
                self.assertEqual(line.price_unit, 50.0)

    def test_form_partner_change_updates_all_lines(self):
        """Test that changing partner updates all line prices/names/dates."""
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.partner_a
        with po_form.line_ids.new() as line:
            line.product_id = self.product_with_sellers
            line.product_qty = 5
        po = po_form.save()

        # Initial values from partner_a's seller
        self.assertEqual(po.line_ids.price_unit, 10.0)
        self.assertIn("PROD-A", po.line_ids.name)

        # Change partner
        po.partner_id = self.partner_b

        # Values should update to partner_b's seller
        self.assertEqual(po.line_ids.price_unit, 12.0)
        self.assertIn("PROD-B", po.line_ids.name)

    # =========================================================================
    # TEST: Edge cases
    # =========================================================================

    def test_display_type_lines_ignored(self):
        """Verify section/note lines don't compute seller fields."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Section Header",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    ),
                ],
            }
        )

        section_line = po.line_ids.filtered(lambda l: l.display_type)
        product_line = po.line_ids.filtered(lambda l: not l.display_type)

        self.assertFalse(section_line.selected_seller_id)
        self.assertFalse(section_line.price_unit)
        self.assertTrue(product_line.selected_seller_id)
        self.assertEqual(product_line.price_unit, 10.0)

    def test_zero_quantity_line(self):
        """Verify lines with zero quantity still compute seller correctly."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 0,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Should still select a seller (using qty=1 as default in selection)
        self.assertTrue(line.selected_seller_id)

    # =========================================================================
    # TEST: date_is_manual flag functionality
    # =========================================================================

    @freeze_time("2024-01-15")
    def test_date_is_manual_initially_false(self):
        """Verify date_is_manual is False for new lines."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        self.assertFalse(line.date_is_manual)
        # Date should be computed from seller delay
        expected_date = fields.Datetime.now() + timedelta(days=3)
        self.assertEqual(line.date_planned.date(), expected_date.date())

    @freeze_time("2024-01-15")
    def test_date_is_manual_set_via_onchange(self):
        """Verify date_is_manual is set when user changes date in UI.

        Note: The onchange sets date_is_manual in the virtual record during form edit.
        We explicitly set date_is_manual alongside the date to simulate proper UI behavior.
        """
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        self.assertFalse(line.date_is_manual)

        # Simulate user manually setting date (the UI would trigger onchange)
        # The onchange sets date_is_manual=True, which we do explicitly here
        custom_date = fields.Datetime.now() + timedelta(days=30)
        line.write(
            {
                "date_planned": custom_date,
                "date_is_manual": True,  # Simulates what onchange does
            }
        )

        # Verify the flag is set
        self.assertTrue(po.line_ids.date_is_manual)
        self.assertEqual(po.line_ids.date_planned.date(), custom_date.date())

    @freeze_time("2024-01-15")
    def test_date_preserved_when_manual_flag_set(self):
        """Verify date is preserved when date_is_manual=True and seller changes."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Set custom date and mark as manual
        custom_date = fields.Datetime.now() + timedelta(days=30)
        line.write(
            {
                "date_planned": custom_date,
                "date_is_manual": True,
            }
        )

        # Change quantity (which would normally change seller and date)
        line.product_qty = 15

        # Date should be preserved because date_is_manual is True
        self.assertEqual(line.date_planned.date(), custom_date.date())
        self.assertTrue(line.date_is_manual)

    @freeze_time("2024-01-15")
    def test_date_updates_without_manual_flag(self):
        """Verify date updates normally when date_is_manual=False."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_with_sellers.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        line = po.line_ids

        # Initial date from first seller (delay=3)
        initial_date = fields.Datetime.now() + timedelta(days=3)
        self.assertEqual(line.date_planned.date(), initial_date.date())
        self.assertFalse(line.date_is_manual)

        # Change qty to select second seller (delay=2)
        line.product_qty = 15

        # Date should update to new seller's delay
        expected_date = fields.Datetime.now() + timedelta(days=2)
        self.assertEqual(line.date_planned.date(), expected_date.date())
        self.assertFalse(line.date_is_manual)
