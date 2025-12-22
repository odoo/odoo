# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPackingNeg(TransactionCase):

    def test_packing_neg(self):
        res_partner_2 = self.env['res.partner'].create({
            'name': 'Deco Addict',
            'email': 'deco.addict82@example.com',
        })

        res_partner_4 = self.env['res.partner'].create({
            'name': 'Ready Mat',
            'email': 'ready.mat28@example.com',
        })

        # Create a new "negative" storable product
        product_neg = self.env['product.product'].create({
            'name': 'Negative product',
            'is_storable': True,
            'categ_id': self.ref('product.product_category_1'),
            'list_price': 100.0,
            'standard_price': 70.0,
            'seller_ids': [(0, 0, {
                'delay': 1,
                'partner_id': res_partner_2.id,
                'min_qty': 2.0,})],
            'uom_id': self.ref('uom.product_uom_unit'),
            'uom_po_id': self.ref('uom.product_uom_unit'),
        })

        # Create an incoming picking for this product of 300 PCE from suppliers to stock
        vals = {
            'name': 'Incoming picking (negative product)',
            'partner_id': res_partner_2.id,
            'picking_type_id': self.ref('stock.picking_type_in'),
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock'),
            'move_ids': [(0, 0, {
                'name': 'NEG',
                'product_id': product_neg.id,
                'product_uom': product_neg.uom_id.id,
                'product_uom_qty': 300.00,
                'location_id': self.ref('stock.stock_location_suppliers'),
                'location_dest_id': self.ref('stock.stock_location_stock'),
            })],
            'state': 'draft',
        }
        pick_neg = self.env['stock.picking'].create(vals)
        pick_neg._onchange_picking_type()
        pick_neg.move_ids._onchange_product_id()

        # Confirm and assign picking
        pick_neg.action_confirm()
        pick_neg.action_assign()

        # Put 120 pieces on Palneg 1 (package), 120 pieces on Palneg 2 with lot A and 60 pieces on Palneg 3
        # create lot A
        lot_a = self.env['stock.lot'].create({'name': 'Lot neg', 'product_id': product_neg.id})
        # create package
        package1 = self.env['stock.quant.package'].create({'name': 'Palneg 1'})
        package2 = self.env['stock.quant.package'].create({'name': 'Palneg 2'})
        package3 = self.env['stock.quant.package'].create({'name': 'Palneg 3'})
        # Create package for each line and assign it as result_package_id
        # create pack operation
        pick_neg.move_line_ids[0].write({'result_package_id': package1.id, 'quantity': 120})
        new_pack1 = self.env['stock.move.line'].create({
            'product_id': product_neg.id,
            'product_uom_id': self.ref('uom.product_uom_unit'),
            'picking_id': pick_neg.id,
            'lot_id': lot_a.id,
            'quantity': 120,
            'result_package_id': package2.id,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock')
        })
        new_pack2 = self.env['stock.move.line'].create({
            'product_id': product_neg.id,
            'product_uom_id': self.ref('uom.product_uom_unit'),
            'picking_id': pick_neg.id,
            'result_package_id': package3.id,
            'quantity': 60,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock')
        })

        # Transfer the receipt
        pick_neg.move_ids.picked = True
        pick_neg._action_done()

        # Make a delivery order of 300 pieces to the customer
        vals = {
            'name': 'outgoing picking (negative product)',
            'partner_id': res_partner_4.id,
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_ids': [(0, 0, {
                'name': 'NEG',
                'product_id': product_neg.id,
                'product_uom': product_neg.uom_id.id,
                'product_uom_qty': 300.00,
                'location_id': self.ref('stock.stock_location_stock'),
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
            'state': 'draft',
        }
        delivery_order_neg = self.env['stock.picking'].create(vals)
        delivery_order_neg._onchange_picking_type()
        delivery_order_neg.move_ids._onchange_product_id()

        # Assign and confirm
        delivery_order_neg.action_confirm()
        delivery_order_neg.action_assign()

        # Instead of doing the 300 pieces, you decide to take pallet 1 (do not mention
        # product in operation here) and 140 pieces from lot A/pallet 2 and 10 pieces from pallet 3

        for rec in delivery_order_neg.move_line_ids:
            if rec.package_id.name == 'Palneg 1':
                rec.result_package_id = False
            elif rec.package_id.name == 'Palneg 2' and rec.lot_id.name == 'Lot neg':
                rec.write({
                  'quantity': 140,
                  'result_package_id': False,
                })
            elif rec.package_id.name == 'Palneg 3':
                rec.quantity = 10
                rec.result_package_id = False

        # Process this picking
        delivery_order_neg.move_ids.picked = True
        delivery_order_neg._action_done()

        # Check the quants that you have -20 pieces pallet 2 in stock, and a total quantity
        # of 50 in stock from pallet 3 (should be 20+30, as it has been split by reservation)
        records = self.env['stock.quant'].search([('product_id', '=', product_neg.id), ('quantity', '!=', '0')])
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
        vals = {
            'name': 'reconciling_delivery',
            'partner_id': res_partner_4.id,
            'picking_type_id': self.ref('stock.picking_type_in'),
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock'),
            'move_ids': [(0, 0, {
                'name': 'NEG',
                'product_id': product_neg.id,
                'product_uom': product_neg.uom_id.id,
                'product_uom_qty': 20.0,
                'location_id': self.ref('stock.stock_location_suppliers'),
                'location_dest_id': self.ref('stock.stock_location_stock'),
            })],
            'state': 'draft',
        }
        delivery_reconcile = self.env['stock.picking'].create(vals)
        delivery_reconcile._onchange_picking_type()
        delivery_reconcile.move_ids._onchange_product_id()

        # Receive 20 products with lot neg in stock with a new incoming shipment that should be on pallet 2
        delivery_reconcile.action_confirm()
        lot = self.env["stock.lot"].search([
            ('product_id', '=', product_neg.id),
            ('name', '=', 'Lot neg')], limit=1)
        pack = self.env["stock.quant.package"].search([('name', '=', 'Palneg 2')], limit=1)
        delivery_reconcile.move_line_ids[0].write({'lot_id': lot.id, 'quantity': 20.0, 'result_package_id': pack.id})
        delivery_reconcile.move_ids.picked = True
        delivery_reconcile._action_done()

        # Check the negative quant was reconciled
        neg_quants = self.env['stock.quant'].search([
            ('product_id', '=', product_neg.id),
            ('quantity', '<', 0),
            ('location_id.id', '!=', self.ref('stock.stock_location_suppliers'))])
        self.assertTrue(len(neg_quants) == 0, "Negative quants should have been reconciled")
