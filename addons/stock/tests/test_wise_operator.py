# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestWiseOperator(TransactionCase):

    def test_wise_operator(self):

        # Create a new storable product
        product_wise = self.env['product.product'].create({
            'name': 'Wise Unit',
            'type': 'product',
            'categ_id': self.ref('product.product_category_1'),
            'uom_id': self.ref('uom.product_uom_unit'),
            'uom_po_id': self.ref('uom.product_uom_unit'),
        })

        self.partner = self.env['res.partner'].create({'name': 'Deco Addict'})

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.shelf2 = self.env['stock.location'].create({
            'name': 'Shelf 2',
            'barcode': 1231985,
            'location_id': warehouse.lot_stock_id.id
        })
        self.shelf1 = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'barcode': 1231892,
            'location_id': warehouse.lot_stock_id.id
        })

        self.partner2 = self.env['res.partner'].create({'name': 'Ready Mat'})

        # Create an incoming picking for this product of 10 PCE from suppliers to stock
        vals = {
            'name': 'Incoming picking (wise unit)',
            'partner_id': self.partner.id,
            'picking_type_id': self.ref('stock.picking_type_in'),
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock'),
            'move_lines': [(0, 0, {
                'name': '/',
                'product_id': product_wise.id,
                'product_uom': product_wise.uom_id.id,
                'product_uom_qty': 10.00,
                'location_id': self.ref('stock.stock_location_suppliers'),
                'location_dest_id': self.ref('stock.stock_location_stock'),
            })],
        }
        pick1_wise = self.env['stock.picking'].create(vals)
        pick1_wise.onchange_picking_type()
        pick1_wise.move_lines.onchange_product_id()

        # Confirm and assign picking and prepare partial
        pick1_wise.action_confirm()
        pick1_wise.action_assign()

        # Put 4 pieces in shelf1 and 6 pieces in shelf2
        package1 = self.env['stock.quant.package'].create({'name': 'Pack 1'})
        pick1_wise.move_line_ids[0].write({
            'result_package_id': package1.id,
            'qty_done': 4,
            'location_dest_id': self.shelf1.id
        })
        new_pack1 = self.env['stock.move.line'].create({
            'product_id': product_wise.id,
            'product_uom_id': self.ref('uom.product_uom_unit'),
            'picking_id': pick1_wise.id,
            'qty_done': 6.0,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.shelf2.id
        })

        # Transfer the receipt
        pick1_wise._action_done()

        # Check the system created 3 quants
        records = self.env['stock.quant'].search([('product_id', '=', product_wise.id)])
        self.assertEqual(len(records.ids), 3, "The number of quants created is not correct")

        # Make a delivery order of 5 pieces to the customer
        vals = {
            'name': 'outgoing picking 1 (wise unit)',
            'partner_id': self.partner2.id,
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_lines': [(0, 0, {
                'name': '/',
                'product_id': product_wise.id,
                'product_uom': product_wise.uom_id.id,
                'product_uom_qty': 5.0,
                'location_id': self.ref('stock.stock_location_stock'),
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        }
        delivery_order_wise1 = self.env['stock.picking'].create(vals)
        delivery_order_wise1.onchange_picking_type()
        delivery_order_wise1.move_lines.onchange_product_id()

        # Assign and confirm
        delivery_order_wise1.action_confirm()
        delivery_order_wise1.action_assign()
        self.assertEqual(delivery_order_wise1.state, 'assigned')

        # Make a delivery order of 5 pieces to the customer
        vals = {
            'name': 'outgoing picking 2 (wise unit)',
            'partner_id': self.partner2.id,
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_lines': [(0, 0, {
                'name': '/',
                'product_id': product_wise.id,
                'product_uom': product_wise.uom_id.id,
                'product_uom_qty': 5.0,
                'location_id': self.ref('stock.stock_location_stock'),
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        }
        delivery_order_wise2 = self.env['stock.picking'].create(vals)
        delivery_order_wise2.onchange_picking_type()
        delivery_order_wise2.move_lines.onchange_product_id()

        # Assign and confirm
        delivery_order_wise2.action_confirm()
        delivery_order_wise2.action_assign()
        self.assertEqual(delivery_order_wise2.state, 'assigned')

        # The operator is a wise guy and decides to do the opposite of what Odoo proposes.
        # He uses the products reserved on picking 1 on picking 2 and vice versa
        move1 = delivery_order_wise1.move_lines[0]
        move2 = delivery_order_wise2.move_lines[0]
        pack_ids1 = delivery_order_wise1.move_line_ids
        pack_ids2 = delivery_order_wise2.move_line_ids

        self.assertEqual(pack_ids1.location_id.id, self.shelf2.id)
        self.assertEqual(set(pack_ids2.mapped('location_id.id')), set([
            self.shelf1.id,
            self.shelf2.id]))

        # put the move lines from delivery_order_wise2 into delivery_order_wise1
        for pack_id2 in pack_ids2:
            new_pack_id1 = pack_id2.copy(default={'picking_id': delivery_order_wise1.id, 'move_id': move1.id})
            new_pack_id1.qty_done = pack_id2.product_qty

        new_move_lines = delivery_order_wise1.move_line_ids.filtered(lambda p: p.qty_done)
        self.assertEqual(sum(new_move_lines.mapped('product_qty')), 0)
        self.assertEqual(sum(new_move_lines.mapped('qty_done')), 5)
        self.assertEqual(set(new_move_lines.mapped('location_id.id')), set([
            self.shelf1.id,
            self.shelf2.id]))

        # put the move line from delivery_order_wise1 into delivery_order_wise2
        new_pack_id2 = pack_ids1.copy(default={'picking_id': delivery_order_wise2.id, 'move_id': move2.id})
        new_pack_id2.qty_done = pack_ids1.product_qty

        new_move_lines = delivery_order_wise2.move_line_ids.filtered(lambda p: p.qty_done)
        self.assertEqual(len(new_move_lines), 1)
        self.assertEqual(sum(new_move_lines.mapped('product_qty')), 0)
        self.assertEqual(sum(new_move_lines.mapped('qty_done')), 5)
        self.assertEqual(new_move_lines.location_id.id, self.shelf2.id)

        # Process this picking
        delivery_order_wise1._action_done()

        # Check there was no negative quant created by this picking

        records = self.env['stock.quant'].search([
            ('product_id', '=', product_wise.id),
            ('quantity', '<', 0.0),
            ('location_id.id', '=', self.ref('stock.stock_location_stock'))])
        self.assertEqual(len(records.ids), 0, 'This should not have created a negative quant')

        # Check the other delivery order has changed its state back to ready
        self.assertEqual(delivery_order_wise2.state, 'assigned', "Delivery order 2 should be back in ready state")

        # Process the second picking
        delivery_order_wise2._action_done()

        # Check all quants are in Customers and there are no negative quants anymore
        records = self.env['stock.quant'].search([
            ('product_id', '=', product_wise.id),
            ('location_id', '!=', self.ref('stock.stock_location_suppliers'))])
        self.assertTrue(all([x.location_id.id == self.ref('stock.stock_location_customers') and x.quantity > 0.0 or
                             x.location_id.id != self.ref('stock.stock_location_customers') and x.quantity == 0.0 for x in records]),
                        "Negative quant or wrong location detected")
