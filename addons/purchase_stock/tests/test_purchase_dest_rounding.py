# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon


class TestPurchaseDestRounding(PurchaseTestCommon):

    def test_extra_receipt_move_keeps_dests_when_attach_qty_rounds_to_zero(self):
        """Dest demand below POL UoM rounding should still chain onto the receipt move."""
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_unit.rounding = 0.0001
        uom_roll = self.env['uom.uom'].create({
            'name': 'Roll (100M)',
            'category_id': uom_unit.category_id.id,
            'factor_inv': 100.0,
            'uom_type': 'bigger',
            'rounding': 1.0,
        })
        product = self.env['product.product'].create({
            'name': 'Film',
            'type': 'product',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_roll.id,
            'seller_ids': [(0, 0, {'partner_id': self.partner_1.id})],
        })
        stock_location = self.warehouse_1.lot_stock_id
        production_location = self.env.ref('stock.location_production')
        dest_move = self.env['stock.move'].create({
            'name': 'dest',
            'product_id': product.id,
            'product_uom': uom_unit.id,
            'product_uom_qty': 14.3,
            'location_id': stock_location.id,
            'location_dest_id': production_location.id,
            'procure_method': 'make_to_order',
        })
        dest_move._action_confirm()

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_1.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_qty': 2.0,
                'product_uom': uom_roll.id,
                'price_unit': 10.0,
            })],
        })
        po_line = po.order_line
        po_line.write({'move_dest_ids': [(4, dest_move.id)]})
        po.button_confirm()

        receipt_moves = po.picking_ids.move_ids.filtered(lambda m: m.product_id == product)
        self.assertEqual(len(receipt_moves), 1)
        self.assertIn(dest_move, receipt_moves.move_dest_ids)
