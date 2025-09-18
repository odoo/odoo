# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import float_compare

from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestSalePriceShadow(SaleCommon):
    """Test price_unit and price_unit_shadow field behavior.

    The sale order line uses a dual-field price tracking system:
    - price_unit: User-facing price (can be manual or automatic)
    - price_unit_shadow: Technical field tracking current pricelist price
    - price_is_manual: Boolean flag for manual price overrides

    This allows manual price overrides while maintaining pricelist comparison.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a product with a known price
        cls.test_product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "list_price": 100.0,
                "type": "consu",
            }
        )

        # Create a pricelist with a 10% discount
        cls.discount_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Test Pricelist -10%",
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "compute_price": "percentage",
                            "percent_price": 10.0,
                        }
                    ),
                ],
            }
        )

    # -------------------------------------------------------------------------
    # CREATE FLOW TESTS
    # -------------------------------------------------------------------------

    def test_create_scenario_1_both_fields_explicit(self):
        """Create with both price_unit and price_unit_shadow explicit.

        When both fields differ, should mark as manual.
        """
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 120.0,  # Manual override
                            "price_unit_shadow": 90.0,  # Pricelist price
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        self.assertEqual(line.price_unit, 120.0, "price_unit should be respected")
        self.assertEqual(
            line.price_unit_shadow, 90.0, "price_unit_shadow should be respected"
        )
        self.assertTrue(
            line.price_is_manual, "Should be marked as manual (fields differ)"
        )

    def test_create_scenario_1_both_fields_same(self):
        """Create with both fields explicit and same value.

        When both fields are the same, should NOT mark as manual.
        """
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 90.0,
                            "price_unit_shadow": 90.0,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        self.assertEqual(line.price_unit, 90.0)
        self.assertEqual(line.price_unit_shadow, 90.0)
        self.assertFalse(line.price_is_manual, "Should NOT be manual (fields are same)")

    def test_create_scenario_2_only_price_unit(self):
        """Create with only price_unit - should sync to shadow."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 150.0,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        self.assertEqual(line.price_unit, 150.0)
        self.assertEqual(
            line.price_unit_shadow, 150.0, "Shadow should sync to price_unit"
        )
        self.assertFalse(line.price_is_manual, "Should be automatic pricing")

    def test_create_scenario_3_only_shadow(self):
        """Create with only price_unit_shadow - should sync to price_unit."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit_shadow": 80.0,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        self.assertEqual(line.price_unit, 80.0, "price_unit should sync from shadow")
        self.assertEqual(line.price_unit_shadow, 80.0)
        self.assertFalse(line.price_is_manual, "Should be automatic pricing")

    def test_create_scenario_4_neither_provided(self):
        """Create with neither field - computed from pricelist."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Pricelist gives 10% discount: 100 * 0.9 = 90
        self.assertEqual(line.price_unit, 90.0, "Should compute from pricelist")
        self.assertEqual(
            line.price_unit_shadow, 90.0, "Shadow should match computed price"
        )
        self.assertFalse(line.price_is_manual, "Should be automatic pricing")

    def test_create_scenario_5_manual_flag_explicit(self):
        """Create with explicit manual flag - should be respected."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 100.0,
                            "price_is_manual": True,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        self.assertEqual(line.price_unit, 100.0)
        self.assertTrue(
            line.price_is_manual, "Explicit manual flag should be respected"
        )

    # -------------------------------------------------------------------------
    # WRITE FLOW TESTS - CRITICAL BUG FIX VALIDATION
    # -------------------------------------------------------------------------

    def test_write_single_line_price_change(self):
        """Write price_unit on single line - should mark as manual."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Initially automatic (from pricelist)
        self.assertFalse(line.price_is_manual)

        # User manually changes price
        line.write({"price_unit": 150.0})

        self.assertEqual(line.price_unit, 150.0)
        self.assertTrue(line.price_is_manual, "Manual price change should set flag")

    def test_write_single_line_price_no_change(self):
        """Write same price_unit - should NOT mark as manual."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 100.0,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Initially automatic
        self.assertFalse(line.price_is_manual)

        # Write same value
        line.write({"price_unit": 100.0})

        self.assertFalse(line.price_is_manual, "Same price should NOT mark as manual")

    def test_write_batch_mixed_changes(self):
        """CRITICAL: Batch write with mixed changes - only changed lines marked manual.

        This is the bug we fixed in write() method.
        Before fix: If ANY line changed, ALL lines marked manual.
        After fix: Only lines with actual changes marked manual.
        """
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 100.0,  # Line A
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 200.0,  # Line B
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 100.0,  # Line C (same as A)
                        }
                    ),
                ],
            }
        )
        line_a, line_b, line_c = order.order_line

        # All initially automatic
        self.assertFalse(line_a.price_is_manual)
        self.assertFalse(line_b.price_is_manual)
        self.assertFalse(line_c.price_is_manual)

        # Batch write: set all to 100
        # Line A: 100 -> 100 (no change)
        # Line B: 200 -> 100 (CHANGED)
        # Line C: 100 -> 100 (no change)
        (line_a + line_b + line_c).write({"price_unit": 100.0})

        # CRITICAL: Only line_b should be marked manual
        self.assertFalse(
            line_a.price_is_manual,
            "Line A unchanged (100->100), should remain automatic",
        )
        self.assertTrue(
            line_b.price_is_manual, "Line B changed (200->100), should be marked manual"
        )
        self.assertFalse(
            line_c.price_is_manual,
            "Line C unchanged (100->100), should remain automatic",
        )

    def test_write_batch_all_changed(self):
        """Batch write where all lines change - all marked manual."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 100.0,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 200.0,
                        }
                    ),
                ],
            }
        )
        line_a, line_b = order.order_line

        # All change to 150
        (line_a + line_b).write({"price_unit": 150.0})

        self.assertTrue(line_a.price_is_manual, "Line A changed, should be manual")
        self.assertTrue(line_b.price_is_manual, "Line B changed, should be manual")

    def test_write_batch_none_changed(self):
        """Batch write where no lines change - none marked manual."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 100.0,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 100.0,
                        }
                    ),
                ],
            }
        )
        line_a, line_b = order.order_line

        # Write same value
        (line_a + line_b).write({"price_unit": 100.0})

        self.assertFalse(line_a.price_is_manual, "No change, should remain automatic")
        self.assertFalse(line_b.price_is_manual, "No change, should remain automatic")

    def test_write_with_explicit_manual_flag(self):
        """Write with explicit price_is_manual - should be respected."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Explicitly set manual flag to False even though price changes
        line.write({"price_unit": 150.0, "price_is_manual": False})

        self.assertFalse(
            line.price_is_manual, "Explicit flag should override detection"
        )

    def test_write_shadow_protection(self):
        """Write price_unit_shadow without price_unit - should be stripped.

        This prevents compute interference when views have readonly price_unit.
        """
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 100.0,
                        }
                    ),
                ],
            }
        )
        line = order.order_line
        original_shadow = line.price_unit_shadow

        # Try to write only shadow (simulates readonly view scenario)
        line.write({"price_unit_shadow": 999.0})

        self.assertEqual(
            line.price_unit_shadow,
            original_shadow,
            "Shadow should not update when price_unit not in vals",
        )

    # -------------------------------------------------------------------------
    # COMPUTE FLOW TESTS
    # -------------------------------------------------------------------------

    def test_compute_automatic_price_updates(self):
        """Automatic prices should update when product/qty/uom changes."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Initially: list_price 100 with 10% discount = 90
        self.assertEqual(line.price_unit, 90.0)
        self.assertEqual(line.price_unit_shadow, 90.0)

        # Change product price
        self.test_product.list_price = 200.0
        line.product_id = False
        line.product_id = self.test_product  # Trigger recompute

        # Should update to: 200 with 10% discount = 180
        self.assertEqual(line.price_unit, 180.0)
        self.assertEqual(line.price_unit_shadow, 180.0)

    def test_compute_manual_price_protected(self):
        """Manual prices should NOT update when product/qty/uom changes."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Set manual price
        line.write({"price_unit": 150.0})  # Marks as manual
        self.assertTrue(line.price_is_manual)

        # Change product price
        self.test_product.list_price = 200.0
        line.product_id = False
        line.product_id = self.test_product  # Trigger recompute

        # price_unit should remain at manual value
        self.assertEqual(line.price_unit, 150.0, "Manual price should be protected")

        # But shadow should update to show current pricelist
        self.assertEqual(line.price_unit_shadow, 180.0, "Shadow should track pricelist")

    def test_compute_force_recomputation(self):
        """Manual prices CAN be updated with force_price_recomputation context."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 150.0,
                            "price_is_manual": True,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Change product price
        self.test_product.list_price = 200.0

        # Force recomputation
        line.with_context(force_price_recomputation=True)._compute_price_unit()

        # Should update even though manual
        self.assertEqual(line.price_unit, 180.0, "Should update with force flag")
        self.assertEqual(line.price_unit_shadow, 180.0)

    # -------------------------------------------------------------------------
    # API METHOD TESTS
    # -------------------------------------------------------------------------

    def test_api_set_manual_price(self):
        """set_manual_price() should set price and update shadow."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Initially automatic with pricelist price
        self.assertEqual(line.price_unit, 90.0)
        self.assertFalse(line.price_is_manual)

        # Set manual price
        line.set_manual_price(125.0)

        self.assertEqual(line.price_unit, 125.0, "Should set manual price")
        self.assertEqual(
            line.price_unit_shadow, 90.0, "Shadow should have pricelist price"
        )
        self.assertTrue(line.price_is_manual, "Should mark as manual")

    def test_api_set_manual_price_invoiced_line(self):
        """set_manual_price() should fail on invoiced lines."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Simulate invoiced line
        line.qty_invoiced = 1.0

        with self.assertRaises(
            UserError, msg="Should block price change on invoiced line"
        ):
            line.set_manual_price(150.0)

    def test_api_reset_to_pricelist_price(self):
        """reset_to_pricelist_price() should clear manual flag and update price."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 150.0,
                            "price_is_manual": True,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Reset to pricelist
        line.reset_to_pricelist_price()

        self.assertEqual(line.price_unit, 90.0, "Should reset to pricelist price")
        self.assertEqual(line.price_unit_shadow, 90.0, "Shadow should sync")
        self.assertFalse(line.price_is_manual, "Should clear manual flag")

    def test_api_get_pricelist_price_current(self):
        """get_pricelist_price_current() should return current pricelist without changing line."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 150.0,
                            "price_is_manual": True,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Get current pricelist price
        pricelist_price = line.get_pricelist_price_current()

        self.assertEqual(pricelist_price, 90.0, "Should return pricelist price")
        self.assertEqual(line.price_unit, 150.0, "Should NOT change line price")
        self.assertTrue(line.price_is_manual, "Should NOT change manual flag")

    def test_api_get_pricelist_price_no_product(self):
        """get_pricelist_price_current() should return False for no product."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Section",
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        self.assertFalse(
            line.get_pricelist_price_current(), "Should return False for no product"
        )

    # -------------------------------------------------------------------------
    # PROTECTION LOGIC TESTS
    # -------------------------------------------------------------------------

    def test_protection_invoiced_line(self):
        """Invoiced lines should never update price automatically."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.discount_pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                        }
                    ),
                ],
            }
        )
        line = order.order_line
        original_price = line.price_unit

        # Simulate invoicing
        line.qty_invoiced = 1.0

        # Change product price
        self.test_product.list_price = 200.0
        line.product_id = False
        line.product_id = self.test_product

        # Price should NOT update (accounting integrity)
        self.assertEqual(
            line.price_unit, original_price, "Invoiced line should not update"
        )

    def test_protection_expense_cost_policy(self):
        """Expense lines with cost policy should not update price."""
        expense_product = self.env["product.product"].create(
            {
                "name": "Expense Product",
                "list_price": 100.0,
                "expense_policy": "cost",
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": expense_product.id,
                            "is_expense": True,
                        }
                    ),
                ],
            }
        )
        line = order.order_line
        original_price = line.price_unit

        # Change product price
        expense_product.list_price = 200.0
        line.product_id = False
        line.product_id = expense_product

        # Price should NOT update (expense cost should be fixed)
        self.assertEqual(
            line.price_unit, original_price, "Expense cost line should not update"
        )

    # -------------------------------------------------------------------------
    # EDGE CASES
    # -------------------------------------------------------------------------

    def test_display_type_lines(self):
        """Display lines (sections, notes) should have no price logic."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Section",
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        self.assertFalse(line.price_unit)
        self.assertFalse(line.price_unit_shadow)
        self.assertFalse(line.price_is_manual)

    def test_context_sale_write_from_compute(self):
        """Context flag sale_write_from_compute should bypass manual detection."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.test_product.id,
                            "price_unit": 100.0,
                        }
                    ),
                ],
            }
        )
        line = order.order_line

        # Write with compute context - should NOT mark as manual
        line.with_context(sale_write_from_compute=True).write({"price_unit": 150.0})

        self.assertFalse(
            line.price_is_manual, "Compute context should bypass manual detection"
        )
