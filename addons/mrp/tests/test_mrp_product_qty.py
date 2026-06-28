from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged('post_install', '-at_install')
class TestMrpProductQty(TestMrpCommon):
    """Tests for ProductProduct._compute_mrp_product_qty which computes the
    total quantity of a product manufactured in the last 365 days based on
    done stock.move records linked to completed manufacturing orders."""

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.bom_1.product_qty = 1
        self.bom_1.uom_id = self.uom_dozen

    def _create_and_complete_mo(self, product, bom, qty=1.0, qty_producing=None):
        """Helper: create an MO, produce it, and mark it as done.
        If qty_producing < qty, a backorder is created for the remainder.
        Returns the completed manufacturing order."""
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mo_form.bom_id = bom
        mo_form.product_qty = qty
        mo = mo_form.save()
        mo.action_confirm()

        mo_form = Form(mo)
        mo_form.qty_producing = qty_producing if qty_producing is not None else qty
        mo = mo_form.save()

        action = mo.button_mark_done()
        if isinstance(action, dict) and action.get('res_model'):
            # Partial production triggers a backorder wizard — confirm it
            self.env[action['res_model']].with_context(action['context']).create({}).action_backorder()

        self.assertEqual(mo.state, 'done')
        return mo

    def test_mrp_product_qty_normal_mo(self):
        """Test that mrp_product_qty correctly counts finished product
        quantity from a normal (no byproduct) manufacturing order."""
        self.product_4 = self.product_4

        self.assertEqual(
            self.product_4.mrp_product_qty, 0.0,
            "Before manufacturing, product qty should be 0",
        )

        self._create_and_complete_mo(self.product_4, self.bom_1, qty=5.0)

        self.product_4.invalidate_recordset(['mrp_product_qty'])
        self.assertEqual(
            self.product_4.mrp_product_qty, 5.0,
            "After manufacturing 5 units, mrp_product_qty should be 5.0",
        )

        self._create_and_complete_mo(self.product_4, self.bom_1, qty=3.0)

        self.product_4.invalidate_recordset(['mrp_product_qty'])
        self.assertEqual(
            self.product_4.mrp_product_qty, 8.0,
            "After manufacturing 5 + 3 = 8 units total, mrp_product_qty should be 8.0",
        )

    def test_mrp_product_qty_mo_with_byproduct(self):
        """Test that mrp_product_qty correctly counts quantities for both
        the main finished product AND byproducts from a manufacturing order."""
        product_byproduct = self.product_3

        self.bom_1.byproduct_ids = [Command.create({
            'product_id': product_byproduct.id,
            'product_qty': 2,
            'uom_id': product_byproduct.uom_id.id,
            })]

        self.assertEqual(self.product_4.mrp_product_qty, 0.0)
        self.assertEqual(product_byproduct.mrp_product_qty, 0.0)

        # Complete an MO for 4 units of main product
        # This should also produce 4 * 2 = 8 units of byproduct
        self._create_and_complete_mo(self.product_4, self.bom_1, qty=4.0)

        self.product_4.invalidate_recordset(['mrp_product_qty'])
        self.assertEqual(
            self.product_4.mrp_product_qty, 4.0,
            "Main product should show 4.0 manufactured",
        )

        product_byproduct.invalidate_recordset(['mrp_product_qty'])
        self.assertEqual(
            product_byproduct.mrp_product_qty, 8.0,
            "By-product should show 8.0 manufactured (4 MO qty * 2 per unit)",
        )

    def test_mrp_product_qty_actual_vs_planned(self):
        """mrp_product_qty must reflect actual produced qty, not planned qty.
        Scenario: plan=10, force qty_producing=5, validate MO → expect 5, not 10."""

        # Plan 10, but only produce 5 — backorder created for the remaining 5
        self._create_and_complete_mo(self.product_4, self.bom_1, qty=10.0, qty_producing=5.0)

        self.product_4.invalidate_recordset(['mrp_product_qty'])
        self.assertEqual(
            self.product_4.mrp_product_qty, 5.0,
            "mrp_product_qty should reflect the 5 actually produced, not the 10 planned",
        )

    def test_mrp_product_qty_uom_conversion(self):
        """When MOs use different UoMs, quantities must be converted to the
        product's reference UoM and summed. E.g. an MO for 3 units + an MO
        for 1 dozen of the same product should yield 15 units total."""

        # MO 1: 3 dozen
        self._create_and_complete_mo(self.product_4, self.bom_1, qty=3.0)

        # MO 2: 6 units (= 0.5 dozen)
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.bom_id = self.bom_1
        mo_form.uom_id = self.uom_unit
        mo_form.product_qty = 6
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        mo_form.qty_producing = 6
        mo = mo_form.save()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

        self.product_4.invalidate_recordset(['mrp_product_qty'])
        self.assertEqual(
            self.product_4.mrp_product_qty, 3.5,
            "mrp_product_qty should convert UoMs: 3 units + 6 units = 3.5 dozen",
        )
