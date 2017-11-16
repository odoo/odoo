# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPackingNeg(TransactionCase):

    def test_packing_neg(self):

        # Create a new "negative" stockable product 
        product_neg = self.env['product.product'].create({
            'name': 'Negative product',
            'type': 'product',
            'categ_id': self.ref('product.product_category_1'),
            'list_price': 100.0,
            'standard_price': 70.0,
            'seller_ids': [(0, 0, {
                'delay': 1,
                'name': self.ref('base.res_partner_2'),
                'min_qty': 2.0,})],
            'uom_id': self.ref('product.product_uom_unit'),
            'uom_po_id': self.ref('product.product_uom_unit'),
        })

        # Create an incoming picking for this product of 300 PCE from suppliers to stock
        default_get_vals = self.env['stock.picking'].default_get(list(self.env['stock.picking'].fields_get()))
        default_get_vals.update({
            'name': 'Incoming picking (negative product)',
            'partner_id': self.ref('base.res_partner_2'),
            'picking_type_id': self.ref('stock.picking_type_in'),
            'move_lines': [(0, 0, {
                'product_id': product_neg.id,
                'product_uom_qty': 300.00,
                'location_id': self.ref('stock.stock_location_suppliers'),
                'location_dest_id': self.ref('stock.stock_location_stock'),
            })],
        })
        pick_neg = self.env['stock.picking'].new(default_get_vals)
        pick_neg.onchange_picking_type()
        pick_neg.move_lines.onchange_product_id()
        vals = pick_neg._convert_to_write(pick_neg._cache)
        pick_neg = self.env['stock.picking'].create(vals)

        # Confirm and assign picking
        pick_neg.action_confirm()
        pick_neg.action_assign()

        # Put 120 pieces on Palneg 1 (package), 120 pieces on Palneg 2 with lot A and 60 pieces on Palneg 3
        # create lot A
        lot_a = self.env['stock.production.lot'].create({'name': 'Lot neg', 'product_id': product_neg.id})
        # create package
        package1 = self.env['stock.quant.package'].create({'name': 'Palneg 1'})
        package2 = self.env['stock.quant.package'].create({'name': 'Palneg 2'})
        package3 = self.env['stock.quant.package'].create({'name': 'Palneg 3'})
        # Create package for each line and assign it as result_package_id
        # create pack operation
        pick_neg.move_line_ids[0].write({'result_package_id': package1.id, 'qty_done': 120})
        new_pack1 = self.env['stock.move.line'].create({
            'product_id': product_neg.id,
            'product_uom_id': self.ref('product.product_uom_unit'),
            'picking_id': pick_neg.id,
            'lot_id': lot_a.id,
            'qty_done': 120,
            'result_package_id': package2.id,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock')
        })
        new_pack2 = self.env['stock.move.line'].create({
            'product_id': product_neg.id,
            'product_uom_id': self.ref('product.product_uom_unit'),
            'picking_id': pick_neg.id,
            'result_package_id': package3.id,
            'qty_done': 60,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock')
        })

        # Transfer the receipt
        pick_neg.do_transfer()

        # Make a delivery order of 300 pieces to the customer
        default_get_vals = self.env['stock.picking'].default_get(list(self.env['stock.picking'].fields_get()))
        default_get_vals.update({
            'name': 'outgoing picking (negative product)',
            'partner_id': self.ref('base.res_partner_4'),
            'picking_type_id': self.ref('stock.picking_type_out'),
            'move_lines': [(0, 0, {
                'product_id': product_neg.id,
                'product_uom_qty': 300.00,
                'location_id': self.ref('stock.stock_location_stock'),
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        })
        delivery_order_neg = self.env['stock.picking'].new(default_get_vals)
        delivery_order_neg.onchange_picking_type()
        delivery_order_neg.move_lines.onchange_product_id()
        vals = delivery_order_neg._convert_to_write(delivery_order_neg._cache)
        delivery_order_neg = self.env['stock.picking'].create(vals)

        # Assign and confirm
        delivery_order_neg.action_confirm()
        delivery_order_neg.action_assign()

        # Instead of doing the 300 pieces, you decide to take pallet 1 (do not mention
        # product in operation here) and 140 pieces from lot A/pallet 2 and 10 pieces from pallet 3

        for rec in delivery_order_neg.move_line_ids:
            if rec.package_id.name == 'Palneg 1':
                rec.qty_done = rec.product_qty
                rec.result_package_id = False
            elif rec.package_id.name == 'Palneg 2' and rec.lot_id.name == 'Lot neg':
                rec.write({
                  'qty_done': 140,
                  'result_package_id': False,
                })
            elif rec.package_id.name == 'Palneg 3':
                rec.qty_done = 10
                rec.result_package_id = False

        # Process this picking
        delivery_order_neg.do_transfer()

        # Check the quants that you have -20 pieces pallet 2 in stock, and a total quantity
        # of 50 in stock from pallet 3 (should be 20+30, as it has been split by reservation)
        records = self.env['stock.quant'].search([('product_id', '=', product_neg.id)])
        pallet_3_stock_qty = 0
        for rec in records:
            if rec.package_id.name == 'Palneg 2' and rec.location_id.id == self.ref('stock.stock_location_stock'):
                self.assertTrue(rec.quantity == -20, "Should have -20 pieces in stock on pallet 2. Got " + str(rec.quantity))
                self.assertTrue(rec.lot_id.name == 'Lot neg', "It should have kept its Lot")
            elif rec.package_id.name == 'Palneg 3' and rec.location_id.id == self.ref('stock.stock_location_stock'):
                pallet_3_stock_qty += rec.quantity
            else:
                self.assertTrue(rec.location_id.id != self.ref('stock.stock_location_stock'), "Unrecognized quant in stock")
        self.assertEqual(pallet_3_stock_qty, 50, "Should have 50 pieces in stock on pallet 3")

        # Create a picking for reconciling the negative quant
        default_get_vals = self.env['stock.picking'].default_get(list(self.env['stock.picking'].fields_get()))
        default_get_vals.update({
            'name': 'reconciling_delivery',
            'partner_id': self.ref('base.res_partner_4'),
            'picking_type_id': self.ref('stock.picking_type_in'),
            'move_lines': [(0, 0, {
                'product_id': product_neg.id,
                'product_uom_qty': 20.0,
                'location_id': self.ref('stock.stock_location_suppliers'),
                'location_dest_id': self.ref('stock.stock_location_stock'),
            })],
        })
        delivery_reconcile = self.env['stock.picking'].new(default_get_vals)
        delivery_reconcile.onchange_picking_type()
        delivery_reconcile.move_lines.onchange_product_id()
        vals = delivery_reconcile._convert_to_write(delivery_reconcile._cache)
        delivery_reconcile = self.env['stock.picking'].create(vals)

        # Receive 20 products with lot neg in stock with a new incoming shipment that should be on pallet 2
        delivery_reconcile.action_confirm()
        lot = self.env["stock.production.lot"].search([
            ('product_id', '=', product_neg.id),
            ('name', '=', 'Lot neg')], limit=1)
        pack = self.env["stock.quant.package"].search([('name', '=', 'Palneg 2')], limit=1)
        delivery_reconcile.move_line_ids[0].write({'lot_id': lot.id, 'qty_done': 20.0, 'result_package_id': pack.id})
        delivery_reconcile.do_transfer()

        # Check the negative quant was reconciled
        neg_quants = self.env['stock.quant'].search([
            ('product_id', '=', product_neg.id),
            ('quantity', '<', 0),
            ('location_id.id', '!=', self.ref('stock.stock_location_suppliers'))])
        self.assertTrue(len(neg_quants) == 0, "Negative quants should have been reconciled")
