# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestPacking(TransactionCase):

    def test_packing(self):

        # Create a new stockable product

        product1 = self.env['product.product'].create({
            'name': 'Nice product',
            'type': 'product',
            'categ_id': self.ref('product.product_category_1'),
            'list_price': 100.0,
            'standard_price': 70.0,
            'seller_ids': [(0, 0, {
                'delay': 1,
                'name': self.ref('base.res_partner_2'),
                'min_qty': 2.0,
            })],
            'uom_id': self.ref('product.product_uom_unit'),
            'uom_po_id': self.ref('product.product_uom_unit'),
        })

        # Create an incoming picking for this product of 300 PCE from suppliers to stock
        default_get_vals = self.env['stock.picking'].default_get(list(self.env['stock.picking'].fields_get()))
        default_get_vals.update({
            'name': 'Incoming picking',
            'partner_id': self.ref('base.res_partner_2'),
            'picking_type_id': self.ref('stock.picking_type_in'),
            'move_lines': [(0, 0, {
                'product_id': product1.id,
                'product_uom_qty': 300.00,
                'location_id': self.ref('stock.stock_location_suppliers'),
                'location_dest_id': self.ref('stock.stock_location_stock'),
            })],
        })
        pick1 = self.env['stock.picking'].new(default_get_vals)
        pick1.onchange_picking_type()
        pick1.move_lines.onchange_product_id()
        vals = pick1._convert_to_write(pick1._cache)
        pick1 = self.env['stock.picking'].create(vals)

        # Confirm and assign picking
        pick1.action_confirm()
        pick1.action_assign()

        # Put 120 pieces on Pallet 1 (package), 120 pieces on Pallet 2 with lot A and 60 pieces on Pallet 3
        lot_a = self.env['stock.production.lot'].create({
            'name': 'Lot A',
            'product_id': product1.id,
        })

        # create package
        package1 = self.env['stock.quant.package'].create({'name': 'Pallet 1'})
        package2 = self.env['stock.quant.package'].create({'name': 'Pallet 2'})
        package3 = self.env['stock.quant.package'].create({'name': 'Pallet 3'})

        # Create package for each line and assign it as result_package_id
        # create pack operation
        pick1.move_line_ids[0].write({'result_package_id': package1.id, 'qty_done': 120})
        new_pack1 = self.env['stock.move.line'].create({
          'product_id': product1.id,
          'product_uom_id': self.ref('product.product_uom_unit'),
          'picking_id': pick1.id,
          'lot_id': lot_a.id,
          'qty_done': 120.0,
          'result_package_id': package2.id,
          'location_id': self.ref('stock.stock_location_suppliers'),
          'location_dest_id': self.ref('stock.stock_location_stock')
        })
        new_pack2 = self.env['stock.move.line'].create({
          'product_id': product1.id,
          'product_uom_id': self.ref('product.product_uom_unit'),
          'picking_id': pick1.id,
          'result_package_id': package3.id,
          'qty_done': 60.0,
          'location_id': self.ref('stock.stock_location_suppliers'),
          'location_dest_id': self.ref('stock.stock_location_stock')
        })

        # Transfer the receipt
        pick1.action_done()

        # Check the system created 5 quants one with 120 pieces on pallet 1,
        # one with 120 pieces on pallet 2 with lot A and 60 pieces on pallet 3 in stock
        # and 1 with -180 pieces and another with -120 piece lot A in supplier
        quants = self.env['stock.quant'].search([('product_id', '=', product1.id)])
        self.assertTrue(len(quants.ids) == 5, "The number of quants created is not correct")
        for quant in quants:
            if quant.package_id.name == 'Pallet 1':
                self.assertTrue(quant.quantity == 120, "Should have 120 pieces on pallet 1")
            elif quant.package_id.name == 'Pallet 2':
                self.assertTrue(quant.quantity == 120, "Should have 120 pieces on pallet 2")
            elif quant.package_id.name == 'Pallet 3':
                self.assertTrue(quant.quantity == 60, "Should have 60 pieces on pallet 3")

        # Check there is no backorder or extra moves created
        backorder = self.env['stock.picking'].search([('backorder_id', '=', pick1.id)])
        self.assertTrue(not backorder)

        # Check extra moves created
        self.assertTrue(len(pick1.move_lines) == 1)

        # Make a delivery order of 300 pieces to the customer
        default_get_vals = self.env['stock.picking'].default_get(list(self.env['stock.picking'].fields_get()))
        default_get_vals.update({
            'name': 'outgoing picking',
            'partner_id': self.ref('base.res_partner_4'),
            'picking_type_id': self.ref('stock.picking_type_out'),
            'move_lines': [(0, 0, {
                'product_id': product1.id,
                'product_uom_qty': 300.00,
                'location_id': self.ref('stock.stock_location_stock'),
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        })
        delivery_order1 = self.env['stock.picking'].new(default_get_vals)
        delivery_order1.onchange_picking_type()
        delivery_order1.move_lines.onchange_product_id()
        vals = delivery_order1._convert_to_write(delivery_order1._cache)
        delivery_order1 = self.env['stock.picking'].create(vals)

        # Assign and confirm
        delivery_order1.action_confirm()
        delivery_order1.action_assign()

        # Instead of doing the 300 pieces, you decide to take pallet 1 (do not
        # mention product in operation here) and 20 pieces from lot A and 10 pieces from pallet 3
        for rec in delivery_order1.move_line_ids:
            if rec.package_id.name == 'Pallet 1':
                rec.qty_done = 120
                rec.result_package_id = False
            if rec.package_id.name == 'Pallet 2':
                rec.qty_done = 20
                rec.result_package_id = False
            if rec.package_id.name == 'Pallet 3':
                rec.qty_done = 10
                rec.result_package_id = False

        # Process this picking
        delivery_order1.action_done()

        # Check the quants that you have 100 pieces of pallet 2 and 50 pieces of pallet 3 in stock
        records = self.env['stock.quant'].search([('product_id', '=', product1.id)])
        for rec in records:
            if rec.package_id.name == 'Pallet 2' and rec.location_id.id == self.ref('stock.stock_location_stock'):
                self.assertTrue(rec.quantity == 100, "Should have 100 pieces in stock on pallet 2, got " + str(rec.quantity))
            elif rec.package_id.name == 'Pallet 3' and rec.location_id.id == self.ref('stock.stock_location_stock'):
                self.assertTrue(rec.quantity == 50, "Should have 50 pieces in stock on pallet 3")
            else:
                self.assertTrue(rec.location_id.id != self.ref('stock.stock_location_stock'), "Unrecognized quant in stock")

        # Check a backorder was created and on that backorder, prepare partial and process backorder
        backorders = self.env['stock.picking'].search([('backorder_id', '=', delivery_order1.id)])
        self.assertTrue(backorders, "Backorder should have been created")
        backorders.action_assign()
        picking = backorders[0]
        self.assertTrue(len(picking.move_line_ids) == 2, "Wrong number of pack operation")
        for pack_op in picking.move_line_ids:
            self.assertTrue(pack_op.package_id.name in ('Pallet 2', 'Pallet 3'), "Wrong pallet info in pack operation (%s found)" % (pack_op.package_id.name))
            if pack_op.package_id.name == 'Pallet 2':
                self.assertTrue(pack_op.product_qty == 100)
                pack_op.qty_done = 100
            elif pack_op.package_id.name == 'Pallet 3':
                self.assertTrue(pack_op.product_qty == 50)
                pack_op.qty_done = 50
        backorders.action_done()

        # Check there are still 0 pieces in stock
        records = self.env['stock.quant'].search([('product_id', '=', product1.id), ('location_id', '=', self.ref('stock.stock_location_stock'))])
        total_qty = 0
        for rec in records:
            total_qty += rec.quantity
        self.assertTrue(total_qty == 0, "Total quantity in stock should be 0 as the backorder took everything out of stock")
        self.assertTrue(product1.qty_available == 0, "Quantity available should be 0 too")
