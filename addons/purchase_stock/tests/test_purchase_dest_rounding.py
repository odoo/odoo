# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestPurchaseDestRounding(PurchaseTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_unit.rounding = 0.0001
        cls.uom_roll = cls.env['uom.uom'].create({
            'name': 'Roll (100M)',
            'category_id': cls.uom_unit.category_id.id,
            'factor_inv': 100.0,
            'uom_type': 'bigger',
            'rounding': 1.0,
        })
        cls.stock_location = cls.warehouse_1.lot_stock_id
        cls.production_location = cls.env.ref('stock.location_production')

    def _create_product(self):
        return self.env['product.product'].create({
            'name': 'Film',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_roll.id,
            'seller_ids': [(0, 0, {'partner_id': self.partner_1.id})],
        })

    def _confirm_po_with_dest(self, dest_qty_stock, po_qty_rolls, product=None):
        product = product or self._create_product()
        dest_move = self.env['stock.move'].create({
            'name': 'dest',
            'product_id': product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': dest_qty_stock,
            'location_id': self.stock_location.id,
            'location_dest_id': self.production_location.id,
            'procure_method': 'make_to_order',
        })
        dest_move._action_confirm()

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_1.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_qty': po_qty_rolls,
                'product_uom': self.uom_roll.id,
                'price_unit': 10.0,
            })],
        })
        po.order_line.write({'move_dest_ids': [(4, dest_move.id)]})
        po.button_confirm()
        receipt_moves = po.picking_ids.move_ids.filtered(lambda m: m.product_id == product)
        return dest_move, receipt_moves

    def test_extra_receipt_move_keeps_dests_when_attach_qty_rounds_to_zero(self):
        """Dest 14.3 units = 0.143 rolls: attach skipped at POL rounding=1, keep dest on push."""
        dest_move, receipt_moves = self._confirm_po_with_dest(14.3, 2.0)
        self.assertEqual(len(receipt_moves), 1)
        self.assertIn(dest_move, receipt_moves.move_dest_ids)

    def test_real_surplus_extra_move_does_not_attach(self):
        """Dest 500 units = 5 rolls, buy 8: attach keeps dests, surplus extra does not."""
        dest_move, receipt_moves = self._confirm_po_with_dest(500.0, 8.0)
        attached = receipt_moves.filtered(lambda m: dest_move in m.move_dest_ids)
        extra = receipt_moves - attached
        self.assertEqual(len(attached), 1)
        self.assertEqual(len(extra), 1)
        self.assertFalse(extra.move_dest_ids)
        # Without propagate_uom, receipt moves are in stock UoM.
        self.assertAlmostEqual(attached.product_uom_qty, 500.0)
        self.assertAlmostEqual(extra.product_uom_qty, 300.0)

    def test_exact_dest_demand_creates_single_attached_move(self):
        """Dest equals PO qty: only attach move, no surplus extra."""
        dest_move, receipt_moves = self._confirm_po_with_dest(200.0, 2.0)
        self.assertEqual(len(receipt_moves), 1)
        self.assertEqual(receipt_moves.move_dest_ids, dest_move)
        self.assertAlmostEqual(receipt_moves.product_uom_qty, 200.0)

    def test_fractional_attach_and_push_sum_to_pol_in_stock_uom(self):
        """Dest 140 units = 1.4 rolls, buy 2: attach 140 + push 60, dest only on attach."""
        dest_move, receipt_moves = self._confirm_po_with_dest(140.0, 2.0)
        attached = receipt_moves.filtered(lambda m: dest_move in m.move_dest_ids)
        extra = receipt_moves - attached
        self.assertEqual(len(attached), 1)
        self.assertEqual(len(extra), 1)
        self.assertFalse(extra.move_dest_ids)
        self.assertAlmostEqual(attached.product_uom_qty, 140.0)
        self.assertAlmostEqual(extra.product_uom_qty, 60.0)
        self.assertAlmostEqual(sum(receipt_moves.mapped('product_uom_qty')), 200.0)

    def test_sub_half_dest_demand_skips_attach_keeps_dest_on_push(self):
        """Dest 40 units = 0.4 rolls: float_is_zero(0.4, rounding=1), single push with dest."""
        dest_move, receipt_moves = self._confirm_po_with_dest(40.0, 2.0)
        self.assertEqual(len(receipt_moves), 1)
        self.assertIn(dest_move, receipt_moves.move_dest_ids)
        # qty_to_push = 2 - 0.4 = 1.6 rolls -> 160 stock units (default no propagate_uom).
        self.assertAlmostEqual(receipt_moves.product_uom_qty, 160.0)

    def test_propagate_uom_fractional_split_rounds_each_leg_to_pol(self):
        """With stock.propagate_uom, 1.4 + 0.6 rolls become receipt moves of 1 + 1 roll."""
        self.env['ir.config_parameter'].sudo().set_param('stock.propagate_uom', '1')
        dest_move, receipt_moves = self._confirm_po_with_dest(140.0, 2.0)
        attached = receipt_moves.filtered(lambda m: dest_move in m.move_dest_ids)
        extra = receipt_moves - attached
        self.assertEqual(len(attached), 1)
        self.assertEqual(len(extra), 1)
        self.assertEqual(attached.product_uom, self.uom_roll)
        self.assertEqual(extra.product_uom, self.uom_roll)
        self.assertAlmostEqual(attached.product_uom_qty, 1.0)
        self.assertAlmostEqual(extra.product_uom_qty, 1.0)
        self.assertAlmostEqual(sum(receipt_moves.mapped('product_uom_qty')), 2.0)
        self.assertFalse(extra.move_dest_ids)

    def test_propagate_uom_swallowed_dest_keeps_full_pol_qty(self):
        """With propagate_uom, 0.143 attach skipped; push 1.857 rounds to 2 rolls and keeps dest."""
        self.env['ir.config_parameter'].sudo().set_param('stock.propagate_uom', '1')
        dest_move, receipt_moves = self._confirm_po_with_dest(14.3, 2.0)
        self.assertEqual(len(receipt_moves), 1)
        self.assertEqual(receipt_moves.product_uom, self.uom_roll)
        self.assertAlmostEqual(receipt_moves.product_uom_qty, 2.0)
        self.assertIn(dest_move, receipt_moves.move_dest_ids)
