
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestPurchaseAdvanced(AccountTestInvoicingCommon):
    """Advanced tests for purchase order functionality covering gaps in test coverage."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_service = cls.env["product.product"].create(
            {
                "name": "Service Product",
                "type": "service",
                "uom_id": cls.env.ref("uom.product_uom_hour").id,
                "standard_price": 50.0,
            }
        )

    # -------------------------------------------------------------------------
    # MERGE TESTS
    # -------------------------------------------------------------------------

    def test_merge_purchase_orders_with_sections(self):
        """Test merging POs that contain section and note lines."""
        # Create first PO with a section
        po1 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Section A",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        # Create second PO with different section
        po2 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Section B",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_b.id,
                            "product_qty": 3,
                            "price_unit": 200,
                        }
                    ),
                ],
            }
        )

        # Merge the POs
        (po1 | po2).action_merge()

        # Find the merged PO (the one still in draft)
        merged_po = (po1 | po2).filtered(lambda p: p.state == "draft")
        cancelled_po = (po1 | po2).filtered(lambda p: p.state == "cancel")

        self.assertEqual(len(merged_po), 1, "Should have one merged PO")
        self.assertEqual(len(cancelled_po), 1, "Should have one cancelled PO")

        # Check that sections are preserved
        section_lines = merged_po.line_ids.filtered(
            lambda l: l.display_type == "line_section"
        )
        product_lines = merged_po.line_ids.filtered(lambda l: not l.display_type)

        self.assertEqual(len(section_lines), 2, "Both sections should be preserved")
        self.assertEqual(len(product_lines), 2, "Both product lines should exist")

    def test_merge_purchase_orders_consolidate_same_product(self):
        """Test that merging POs consolidates lines for the same product."""
        po1 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        po2 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        (po1 | po2).action_merge()

        merged_po = (po1 | po2).filtered(lambda p: p.state == "draft")
        product_lines = merged_po.line_ids.filtered(
            lambda l: l.product_id == self.product_a
        )

        # Lines with same product, UoM, and price should be consolidated
        self.assertEqual(len(product_lines), 1, "Same product lines should be merged")
        self.assertEqual(product_lines.product_qty, 15, "Quantities should be summed")

    def test_merge_purchase_orders_different_partners_fails(self):
        """Test that merging POs with different partners raises an error."""
        po1 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        po2 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_b.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        with self.assertRaises(UserError):
            (po1 | po2).action_merge()

    def test_merge_purchase_orders_with_notes(self):
        """Test merging POs with note lines."""
        po1 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                    Command.create(
                        {
                            "display_type": "line_note",
                            "name": "Important note for PO1",
                        }
                    ),
                ],
            }
        )

        po2 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_b.id,
                            "product_qty": 3,
                            "price_unit": 200,
                        }
                    ),
                ],
            }
        )

        (po1 | po2).action_merge()

        merged_po = (po1 | po2).filtered(lambda p: p.state == "draft")
        note_lines = merged_po.line_ids.filtered(
            lambda l: l.display_type == "line_note"
        )

        self.assertEqual(len(note_lines), 1, "Note line should be preserved")
        self.assertEqual(note_lines.name, "Important note for PO1")

    # -------------------------------------------------------------------------
    # DUPLICATE DETECTION TESTS
    # -------------------------------------------------------------------------

    def test_duplicate_order_detection(self):
        """Test that duplicate PO detection works correctly.

        Duplicate detection requires partner_ref to be set and matches on:
        - Same partner AND (origin matches other PO's name OR partner_ref matches)
        """
        vendor_ref = "VENDOR-REF-001"

        # Create first PO with partner_ref and confirm it
        po1 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_ref": vendor_ref,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )
        po1.action_confirm()

        # Create a similar PO with same partner_ref (draft state for duplicate detection)
        po2 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_ref": vendor_ref,  # Same vendor reference triggers duplicate detection
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        # Check if duplicates are detected
        # The duplicated_order_ids should include po1 since it has the same partner_ref
        self.assertIn(
            po1,
            po2.duplicated_order_ids,
            "PO with same partner and partner_ref should be detected as duplicate",
        )

    def test_no_duplicate_detection_different_products(self):
        """Test that POs with different products are not marked as duplicates."""
        po1 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )
        po1.action_confirm()

        po2 = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_b.id,
                            "product_qty": 10,
                            "price_unit": 200,
                        }
                    ),
                ],
            }
        )

        self.assertNotIn(
            po1,
            po2.duplicated_order_ids,
            "PO with different products should not be a duplicate",
        )

    # -------------------------------------------------------------------------
    # ACKNOWLEDGMENT TESTS
    # -------------------------------------------------------------------------

    def test_purchase_order_acknowledge(self):
        """Test the acknowledge workflow for RFQs."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        self.assertFalse(po.acknowledged, "New PO should not be acknowledged")

        po.action_acknowledge()

        self.assertTrue(po.acknowledged, "PO should be acknowledged after action")

    # -------------------------------------------------------------------------
    # DISPLAY TYPE CONSTRAINT TESTS
    # -------------------------------------------------------------------------

    def test_section_line_has_null_product_fields(self):
        """Test that section lines have null product-related fields."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Test Section",
                        }
                    ),
                ],
            }
        )

        section_line = po.line_ids[0]
        self.assertEqual(section_line.display_type, "line_section")
        self.assertFalse(section_line.product_id, "Section should have no product")
        self.assertEqual(section_line.product_qty, 0, "Section should have zero qty")
        self.assertEqual(section_line.price_unit, 0, "Section should have zero price")

    def test_note_line_has_null_product_fields(self):
        """Test that note lines have null product-related fields."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "display_type": "line_note",
                            "name": "Test Note",
                        }
                    ),
                ],
            }
        )

        note_line = po.line_ids[0]
        self.assertEqual(note_line.display_type, "line_note")
        self.assertFalse(note_line.product_id, "Note should have no product")
        self.assertEqual(note_line.product_qty, 0, "Note should have zero qty")

    def test_subsection_line_works(self):
        """Test that subsection display type works correctly."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Main Section",
                        }
                    ),
                    Command.create(
                        {
                            "display_type": "line_subsection",
                            "name": "Subsection",
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        subsection = po.line_ids.filtered(lambda l: l.display_type == "line_subsection")
        self.assertEqual(len(subsection), 1)
        self.assertEqual(subsection.name, "Subsection")

    # -------------------------------------------------------------------------
    # LOCK/UNLOCK TESTS
    # -------------------------------------------------------------------------

    def test_lock_prevents_modification(self):
        """Test that locking a PO prevents certain modifications."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )
        po.action_confirm()
        po.action_lock()

        self.assertTrue(po.locked, "PO should be locked")

        # Locked PO should not be cancellable
        with self.assertRaises(UserError):
            po.action_cancel()

    def test_unlock_allows_modification(self):
        """Test that unlocking a PO allows modifications again."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )
        po.action_confirm()
        po.action_lock()
        po.action_unlock()

        self.assertFalse(po.locked, "PO should be unlocked")

    # -------------------------------------------------------------------------
    # CURRENCY TESTS
    # -------------------------------------------------------------------------

    def test_currency_from_partner_property(self):
        """Test that currency is correctly set from partner's purchase currency."""
        eur = self.env.ref("base.EUR")
        self.partner_a.property_purchase_currency_id = eur

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        self.assertEqual(
            po.currency_id, eur, "PO currency should match partner's purchase currency"
        )

    # -------------------------------------------------------------------------
    # INVOICE STATE TESTS
    # -------------------------------------------------------------------------

    def test_invoice_state_no_invoice(self):
        """Test invoice state when no invoice exists.

        Uses a service product with bill_policy='ordered' so that
        invoice_state is 'to do' immediately after confirmation.
        Products with bill_policy='transferred' show 'no' until received.
        """
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_service.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )
        po.action_confirm()

        self.assertEqual(
            po.invoice_state,
            "to do",
            "Invoice state should be 'to do' for service products",
        )

    def test_invoice_state_partial(self):
        """Test invoice state with partial invoicing.

        Uses a service product with bill_policy='ordered' to test partial invoicing.
        """
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_service.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )
        po.action_confirm()

        # Create partial invoice linked to the PO line
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_service.id,
                            "quantity": 5,  # Only half of the ordered quantity
                            "price_unit": 100,
                            "purchase_line_ids": [Command.set(po.line_ids.ids)],
                        }
                    ),
                ],
            }
        )
        invoice.action_post()

        self.assertEqual(
            po.invoice_state,
            "partial",
            "Invoice state should be 'partial' when partially invoiced",
        )

    # -------------------------------------------------------------------------
    # AMOUNT COMPUTATION TESTS
    # -------------------------------------------------------------------------

    def test_amount_computation_with_taxes(self):
        """Test that amounts are correctly computed with taxes."""
        tax_15 = self.env["account.tax"].create(
            {
                "name": "Tax 15%",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 15,
            }
        )

        self.product_a.supplier_taxes_id = [Command.set([tax_15.id])]

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )

        self.assertEqual(po.amount_untaxed, 1000, "Untaxed amount should be 1000")
        self.assertEqual(po.amount_tax, 150, "Tax amount should be 150 (15%)")
        self.assertEqual(po.amount_total, 1150, "Total should be 1150")

    def test_amount_computation_with_discount(self):
        """Test that amounts are correctly computed with discounts."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 100,
                            "discount": 10,  # 10% discount
                        }
                    ),
                ],
            }
        )

        self.assertEqual(
            po.amount_untaxed, 900, "Untaxed amount should be 900 after 10% discount"
        )


@tagged("-at_install", "post_install")
class TestPurchaseOrderLineConstraints(AccountTestInvoicingCommon):
    """Tests for purchase order line constraints and validations."""

    def test_cannot_delete_invoiced_line(self):
        """Test that invoiced lines cannot be deleted."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                        }
                    ),
                ],
            }
        )
        po.action_confirm()

        # Create and post invoice
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 5,
                            "price_unit": 100,
                            "purchase_line_ids": [Command.set(po.line_ids.ids)],
                        }
                    ),
                ],
            }
        )
        invoice.action_post()

        # Try to delete the line
        with self.assertRaises(UserError):
            po.line_ids.unlink()

    def test_line_sequence_preserved(self):
        """Test that line sequence is preserved correctly."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Section 1",
                            "sequence": 10,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 5,
                            "price_unit": 100,
                            "sequence": 20,
                        }
                    ),
                    Command.create(
                        {
                            "display_type": "line_section",
                            "name": "Section 2",
                            "sequence": 30,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_b.id,
                            "product_qty": 3,
                            "price_unit": 200,
                            "sequence": 40,
                        }
                    ),
                ],
            }
        )

        lines = po.line_ids.sorted("sequence")
        self.assertEqual(lines[0].name, "Section 1")
        self.assertEqual(lines[1].product_id, self.product_a)
        self.assertEqual(lines[2].name, "Section 2")
        self.assertEqual(lines[3].product_id, self.product_b)
