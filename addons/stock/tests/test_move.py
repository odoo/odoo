# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class StockMove(TransactionCase):
    def setUp(self):
        super(StockMove, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.pack_location = self.env.ref('stock.location_pack_zone')
        self.uom_unit = self.env.ref('product.product_uom_unit')
        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.product2 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.product3 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'lot',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.product4 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

    def test_in_1(self):
        """ Receive products from a supplier. Check that a move line is created and that the
        reception correctly increase a single quant in stock.
        """
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # fill the move line
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 100.0)
        self.assertEqual(move_line.qty_done, 0.0)
        move_line.qty_done = 100.0

        # validation
        move1.action_done()
        self.assertEqual(move1.state, 'done')
        # no quants are created in the supplier location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.supplier_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 100.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.supplier_location)), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)

    def test_in_2(self):
        """ Receive 5 tracked products from a supplier. The create move line should have 5
        reserved. If i assign the 5 items to lot1, the reservation should not change. Once
        i validate, the reception correctly increase a single quant in stock.
        """
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 5)
        move_line.lot_name = 'lot1'
        move_line.qty_done = 5.0
        self.assertEqual(move_line.product_qty, 5)  # don't change reservation

        move1.action_done()
        self.assertEqual(move_line.product_qty, 5)  # don't change reservation
        self.assertEqual(move1.state, 'done')

        # no quants are created in the supplier location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.supplier_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location), 5.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product3, self.supplier_location)), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product3, self.stock_location)), 1.0)

    def test_in_3(self):
        """ Receive 5 serial-tracked products from a supplier. The system should create 5 differents
        move line.
        """
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 5)
        move_line = move1.move_line_ids[0]
        self.assertEqual(move1.reserved_availability, 5)

        i = 0
        for move_line in move1.move_line_ids:
            move_line.lot_name = 'sn%s' % i
            move_line.qty_done = 1
            i += 1
        self.assertEqual(move1.quantity_done, 5.0)
        self.assertEqual(move1.product_qty, 5)  # don't change reservation

        move1.action_done()

        self.assertEqual(move1.quantity_done, 5.0)
        self.assertEqual(move1.product_qty, 5)  # don't change reservation
        self.assertEqual(move1.state, 'done')

        # no quants are created in the supplier location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.supplier_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 5.0)

        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.supplier_location)), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location)), 5.0)

    def test_out_1(self):
        """ Send products to a client. Check that a move line is created reserving products in
        stock and that the delivery correctly remove the single quant in stock.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 100)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 100.0)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        # Should be a reserved quantity and thus a quant.
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)

        # fill the move line
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 100.0)
        self.assertEqual(move_line.qty_done, 0.0)
        move_line.qty_done = 100.0

        # validation
        move1.action_done()
        self.assertEqual(move1.state, 'done')
        # # no quants are created in the customer location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.customer_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.customer_location)), 0.0)
        # there should be no quant amymore in the stock location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 0.0)

    def test_out_2(self):
        """ Send a consumable product to a client. Check that a move line is created but
            quants are not impacted.
        """
        # make some stock

        self.product1.type = 'consu'
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        # Should be a reserved quantity and thus a quant.
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 0.0)

        # fill the move line
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 100.0)
        self.assertEqual(move_line.qty_done, 0.0)
        move_line.qty_done = 100.0

        # validation
        move1.action_done()
        self.assertEqual(move1.state, 'done')
        # # no quants are created in the customer location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.customer_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.customer_location)), 0.0)
        # there should be no quant amymore in the stock location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 0.0)

    def test_mixed_tracking_reservation_1(self):
        """ Send products tracked by lot to a customer. In your stock, there are tracked and
        untracked quants. Two moves lines should be created: one for the tracked ones, another
        for the untracked ones.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product3.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product3, self.stock_location, 2)
        self.env['stock.quant']._update_available_quantity(self.product3, self.stock_location, 3, lot_id=lot1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location), 5.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move1.action_confirm()
        move1.action_assign()

        self.assertEqual(len(move1.move_line_ids), 2)

    def test_mixed_tracking_reservation_2(self):
        """ Send products tracked by lot to a customer. In your stock, there two tracked and
        mulitple untracked quants. There should be as many move lines as there are quants
        reserved. Edit the reserve move lines to set them to new serial numbers, the reservation
        should stay. Validate and the final quantity in stock should be 0, not negative.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product2.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product2.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 2)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1, lot_id=lot2)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 4.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4.0,
        })
        move1.action_confirm()
        move1.action_assign()
        self.assertEqual(len(move1.move_line_ids), 4)
        for ml in move1.move_line_ids:
            self.assertEqual(ml.product_qty, 1.0)

        # assign lot3 and lot 4 to both untracked move lines
        lot3 = self.env['stock.production.lot'].create({
            'name': 'lot3',
            'product_id': self.product2.id,
        })
        lot4 = self.env['stock.production.lot'].create({
            'name': 'lot4',
            'product_id': self.product2.id,
        })
        untracked_move_line = move1.move_line_ids.filtered(lambda ml: not ml.lot_id)
        untracked_move_line[0].lot_id = lot3
        untracked_move_line[1].lot_id = lot4
        for ml in move1.move_line_ids:
            self.assertEqual(ml.product_qty, 1.0)

        # no changes on quants, even if i made some move lines with a lot id whom reserved on untracked quants
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, strict=True)), 1.0)  # with a qty of 2
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot1, strict=True)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot2, strict=True)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot3, strict=True)), 0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot4, strict=True)), 0)

        move1.move_line_ids.write({'qty_done': 1.0})

        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot2, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot3, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot4, strict=True), 0.0)

    def test_mixed_tracking_reservation_3(self):
        """ Send two products tracked by lot to a customer. In your stock, there two tracked quants
        and two untracked. Once the move is validated, add move lines to also move the two untracked
        ones and assign them serial numbers on the fly. The final quantity in stock should be 0, not
        negative.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product2.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product2.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1, lot_id=lot2)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 2.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.write({'qty_done': 1.0})
        move1.action_done()

        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 2)
        lot3 = self.env['stock.production.lot'].create({
            'name': 'lot3',
            'product_id': self.product2.id,
        })
        lot4 = self.env['stock.production.lot'].create({
            'name': 'lot4',
            'product_id': self.product2.id,
        })

        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'qty_done': 1,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
            'lot_id': lot3.id,
        })
        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'qty_done': 1,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
            'lot_id': lot4.id
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot2, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot3, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot4, strict=True), 0.0)

    def test_mixed_tracking_reservation_4(self):
        """ Send two products tracked by lot to a customer. In your stock, there two tracked quants
        and on untracked. Once the move is validated, edit one of the done move line to change the
        serial number to one that is not in stock. The original serial should go back to stock and
        the untracked quant should be tracked on the fly and sent instead.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product2.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product2.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1, lot_id=lot2)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 2.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.write({'qty_done': 1.0})
        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot2, strict=True), 0.0)

        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1)
        lot3 = self.env['stock.production.lot'].create({
            'name': 'lot3',
            'product_id': self.product2.id,
        })

        move1.with_context(debug=True).move_line_ids[1].lot_id = lot3

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot2, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot3, strict=True), 0.0)

    def test_mixed_tracking_reservation_5(self):
        move1 = self.env['stock.move'].create({
            'name': 'test_jenaimarre_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        self.assertEqual(move1.state, 'confirmed')

        # create an untracked quant
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1.0)
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product2.id,
        })

        # create a new move line with a lot not assigned to any quant
        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'qty_done': 1,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
            'lot_id': lot1.id
        })
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.reserved_availability, 0)

        # validating the move line should move the lot, not create a negative quant in stock
        move1.action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location)), 0.0)

    def test_mixed_tracking_reservation_6(self):
        # create an untracked quant
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1.0)
        move1 = self.env['stock.move'].create({
            'name': 'test_jenaimarre_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')

        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product2.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product2.id,
        })

        move_line = move1.move_line_ids
        move_line.lot_id = lot1
        self.assertEqual(move_line.product_qty, 1.0)
        move_line.lot_id = lot2
        self.assertEqual(move_line.product_qty, 1.0)
        move_line.qty_done = 1

        # validating the move line should move the lot, not create a negative quant in stock
        move1.action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location)), 0.0)

    def test_mixed_tracking_reservation_7(self):
        """ Similar test_mixed_tracking_reservation_2 but creates first the tracked quant, then the
        untracked ones. When adding a lot to the untracked move line, it should not decrease the
        untracked quant then increase a non-existing tracked one that will fallback on the
        untracked quant.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product2.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product2.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 2.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move1.action_confirm()
        move1.action_assign()
        self.assertEqual(len(move1.move_line_ids), 2)
        for ml in move1.move_line_ids:
            self.assertEqual(ml.product_qty, 1.0)

        untracked_move_line = move1.move_line_ids.filtered(lambda ml: not ml.lot_id).lot_id = lot2
        for ml in move1.move_line_ids:
            self.assertEqual(ml.product_qty, 1.0)

        move1.move_line_ids.write({'qty_done': 1.0})

        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot2, strict=True), 0.0)
        quants = self.env['stock.quant']._gather(self.product2, self.stock_location)
        self.assertEqual(len(quants), 0)

    def test_putaway_1(self):
        """ Receive products from a supplier. Check that putaway rules are rightly applied on
        the receipt move line.
        """
        # This test will apply a putaway strategy on the stock location to put everything
        # incoming in the sublocation shelf1.
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        putaway = self.env['product.putaway'].create({
            'name': 'putaway stock->shelf1',
            'fixed_location_ids': [(0, 0, {
                'category_id': self.env.ref('product.product_category_all').id,
                'fixed_location_id': shelf1_location.id,
            })]
        })
        self.stock_location.write({
            'putaway_strategy_id': putaway.id,
        })

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf1_location.id)

    def test_availability_1(self):
        """ Check that the `availability` field on a move is correctly computed when there is
        more than enough products in stock.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 150.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 150.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)
        self.assertEqual(move1.availability, 100.0)

    def test_availability_2(self):
        """ Check that the `availability` field on a move is correctly computed when there is
        not enough products in stock.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 50.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 50.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)
        self.assertEqual(move1.availability, 50.0)

    def test_unreserve_1(self):
        """ Check that unreserving a stock move sets the products reserved as available and
        set the state back to confirmed.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 150.0)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 150.0)
        self.assertEqual(move1.availability, 100.0)

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 50.0)

        # unreserve
        move1.do_unreserve()
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 150.0)
        self.assertEqual(move1.state, 'confirmed')

    def test_unreserve_2(self):
        """ Check that unreserving a stock move sets the products reserved as available and
        set the state back to confirmed even if they are in a pack.
        """
        package1 = self.env['stock.quant.package'].create({'name': 'test_unreserve_2_pack'})

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 150.0, package_id=package1)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 150.0)
        self.assertEqual(move1.availability, 100.0)

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 50.0)

        # unreserve
        move1.do_unreserve()
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 150.0)
        self.assertEqual(move1.state, 'confirmed')

    def test_unreserve_3(self):
        """ Similar to `test_unreserve_1` but checking the quants more in details.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        quants = self.env['stock.quant']._gather(self.product1, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 2.0)

        move1.do_unreserve()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 0.0)
        self.assertEqual(len(move1.move_line_ids), 0.0)

    def test_unreserve_4(self):
        """ Check the unreservation of a partially available stock move.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'partially_available')
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        quants = self.env['stock.quant']._gather(self.product1, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 2.0)

        move1.do_unreserve()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 0.0)
        self.assertEqual(len(move1.move_line_ids), 0.0)

    def test_unreserve_5(self):
        """ Check the unreservation of a stock move reserved on multiple quants.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 3)
        self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
            'quantity': 2,
        })
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 5)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_unreserve_5',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        move1.do_unreserve()

        quants = self.env['stock.quant']._gather(self.product1, self.stock_location)
        self.assertEqual(len(quants), 2.0)
        for quant in quants:
            self.assertEqual(quant.reserved_quantity, 0)

    def test_link_assign_1(self):
        """ Test the assignment mechanism when two chained stock moves try to move one unit of an
        untracked product.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)

        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust).action_confirm()
        move_stock_pack.action_assign()
        move_stock_pack.move_line_ids[0].qty_done = 1.0
        move_stock_pack.action_done()
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)
        move_line = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line.location_id.id, self.pack_location.id)
        self.assertEqual(move_line.location_dest_id.id, self.customer_location.id)
        self.assertEqual(move_pack_cust.state, 'assigned')

    def test_link_assign_2(self):
        """ Test the assignment mechanism when two chained stock moves try to move one unit of a
        tracked product.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product1.id,
        })

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot1)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location, lot1)), 1.0)

        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_2_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_2_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust).action_confirm()
        move_stock_pack.action_assign()

        move_line_stock_pack = move_stock_pack.move_line_ids[0]
        self.assertEqual(move_line_stock_pack.lot_id.id, lot1.id)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location, lot1)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.pack_location, lot1)), 0.0)

        move_line_stock_pack.qty_done = 1.0
        move_stock_pack.action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location, lot1)), 0.0)

        move_line_pack_cust = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line_pack_cust.lot_id.id, lot1.id)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.pack_location, lot_id=lot1), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.pack_location, lot1)), 1.0)

    def test_link_assign_3(self):
        """ Test the assignment mechanism when three chained stock moves (2 sources, 1 dest) try to
        move multiple units of an untracked product.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)

        move_stock_pack_1 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_stock_pack_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move_stock_pack_1.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_stock_pack_2.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, [move_stock_pack_1.id, move_stock_pack_2.id], 0)]})

        (move_stock_pack_1 + move_stock_pack_2 + move_pack_cust).action_confirm()

        # assign and fulfill the first move
        move_stock_pack_1.action_assign()
        self.assertEqual(move_stock_pack_1.state, 'assigned')
        self.assertEqual(len(move_stock_pack_1.move_line_ids), 1)
        move_stock_pack_1.move_line_ids[0].qty_done = 1.0
        move_stock_pack_1.action_done()
        self.assertEqual(move_stock_pack_1.state, 'done')

        # the destination move should be partially available and have one move line
        self.assertEqual(move_pack_cust.state, 'partially_available')
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)
        # Should have 1 quant in stock_location and another in pack_location
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.pack_location)), 1.0)

        move_stock_pack_2.action_assign()
        self.assertEqual(move_stock_pack_2.state, 'assigned')
        self.assertEqual(len(move_stock_pack_2.move_line_ids), 1)
        move_stock_pack_2.move_line_ids[0].qty_done = 1.0
        move_stock_pack_2.action_done()
        self.assertEqual(move_stock_pack_2.state, 'done')

        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.pack_location)), 1.0)

        self.assertEqual(move_pack_cust.state, 'assigned')
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)
        move_line_1 = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line_1.location_id.id, self.pack_location.id)
        self.assertEqual(move_line_1.location_dest_id.id, self.customer_location.id)
        self.assertEqual(move_line_1.product_qty, 2.0)
        self.assertEqual(move_pack_cust.state, 'assigned')

    def test_link_assign_4(self):
        """ Test the assignment mechanism when three chained stock moves (2 sources, 1 dest) try to
        move multiple units of a tracked by lot product.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product1.id,
        })

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2.0, lot_id=lot1)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location, lot1)), 1.0)

        move_stock_pack_1 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_stock_pack_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move_stock_pack_1.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_stock_pack_2.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, [move_stock_pack_1.id, move_stock_pack_2.id], 0)]})

        (move_stock_pack_1 + move_stock_pack_2 + move_pack_cust).action_confirm()

        # assign and fulfill the first move
        move_stock_pack_1.action_assign()
        self.assertEqual(len(move_stock_pack_1.move_line_ids), 1)
        self.assertEqual(move_stock_pack_1.move_line_ids[0].lot_id.id, lot1.id)
        move_stock_pack_1.move_line_ids[0].qty_done = 1.0
        move_stock_pack_1.action_done()

        # the destination move should be partially available and have one move line
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)

        move_stock_pack_2.action_assign()
        self.assertEqual(len(move_stock_pack_2.move_line_ids), 1)
        self.assertEqual(move_stock_pack_2.move_line_ids[0].lot_id.id, lot1.id)
        move_stock_pack_2.move_line_ids[0].qty_done = 1.0
        move_stock_pack_2.action_done()

        self.assertEqual(len(move_pack_cust.move_line_ids), 1)
        move_line_1 = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line_1.location_id.id, self.pack_location.id)
        self.assertEqual(move_line_1.location_dest_id.id, self.customer_location.id)
        self.assertEqual(move_line_1.product_qty, 2.0)
        self.assertEqual(move_line_1.lot_id.id, lot1.id)
        self.assertEqual(move_pack_cust.state, 'assigned')

    def test_link_assign_5(self):
        """ Test the assignment mechanism when three chained stock moves (1 sources, 2 dest) try to
        move multiple units of an untracked product.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2.0)

        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move_pack_cust_1 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust_1.id, move_pack_cust_2.id, 0)]})
        move_pack_cust_1.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})
        move_pack_cust_2.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust_1 + move_pack_cust_2).action_confirm()

        # assign and fulfill the first move
        move_stock_pack.action_assign()
        self.assertEqual(len(move_stock_pack.move_line_ids), 1)
        move_stock_pack.move_line_ids[0].qty_done = 2.0
        move_stock_pack.action_done()

        # the destination moves should be available and have one move line
        self.assertEqual(len(move_pack_cust_1.move_line_ids), 1)
        self.assertEqual(len(move_pack_cust_2.move_line_ids), 1)

        move_pack_cust_1.move_line_ids[0].qty_done = 1.0
        move_pack_cust_2.move_line_ids[0].qty_done = 1.0
        (move_pack_cust_1 + move_pack_cust_2).action_done()

    def test_link_assign_6(self):
        """ Test the assignment mechanism when four chained stock moves (2 sources, 2 dest) try to
        move multiple units of an untracked by lot product. This particular test case simulates a two
        step receipts with backorder.
        """
        move_supp_stock_1 = self.env['stock.move'].create({
            'name': 'test_link_assign_6_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move_supp_stock_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_6_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move_stock_stock_1 = self.env['stock.move'].create({
            'name': 'test_link_assign_6_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move_stock_stock_1.write({'move_orig_ids': [(4, [move_supp_stock_1.id, move_supp_stock_2.id], 0)]})
        move_stock_stock_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_6_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move_stock_stock_2.write({'move_orig_ids': [(4, [move_supp_stock_1.id, move_supp_stock_2.id], 0)]})

        (move_supp_stock_1 + move_supp_stock_2 + move_stock_stock_1 + move_stock_stock_2).action_confirm()
        move_supp_stock_1.action_assign()
        self.assertEqual(move_supp_stock_1.state, 'assigned')
        self.assertEqual(move_supp_stock_2.state, 'confirmed')
        self.assertEqual(move_stock_stock_1.state, 'waiting')
        self.assertEqual(move_stock_stock_2.state, 'waiting')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        # do the fist move, it'll bring 3 units in stock location so only `move_stock_stock_1`
        # should be assigned
        move_supp_stock_1.move_line_ids.qty_done = 3.0
        move_supp_stock_1.action_done()
        self.assertEqual(move_supp_stock_1.state, 'done')
        self.assertEqual(move_supp_stock_2.state, 'confirmed')
        self.assertEqual(move_stock_stock_1.state, 'assigned')
        self.assertEqual(move_stock_stock_2.state, 'waiting')

    def test_use_unreserved_move_line_1(self):
        """ Test that validating a stock move linked to an untracked product reserved by another one
        correctly unreserves the other one.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0)

        # prepare the conflicting move
        move1 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })

        # reserve those move
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        move1.action_confirm()
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        move2.action_confirm()
        move2.action_assign()
        self.assertEqual(move2.state, 'confirmed')

        # force assign the second one
        move2.force_assign()
        self.assertEqual(move2.state, 'assigned')

        # use the product from the first one
        move2.write({'move_line_ids': [(0, 0, {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'qty_done': 1,
            'product_uom_qty': 0,
            'lot_id': False,
            'package_id': False,
            'result_package_id': False,
            'location_id': move2.location_id.id,
            'location_dest_id': move2.location_dest_id.id,
        })]})
        move2.action_done()

        # the first move should go back to confirmed
        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

    def test_use_unreserved_move_line_2(self):
        """ Test that validating a stock move linked to a tracked product reserved by another one
        correctly unreserves the other one.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product1.id,
        })

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot1)

        # prepare the conflicting move
        move1 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })

        # reserve those move
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 1.0)
        move1.action_confirm()
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        move2.action_confirm()
        move2.action_assign()
        self.assertEqual(move2.state, 'confirmed')

        # force assign the second one
        move2.force_assign()
        self.assertEqual(move2.state, 'assigned')

        # use the product from the first one
        move2.write({'move_line_ids': [(0, 0, {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'qty_done': 1,
            'product_uom_qty': 0,
            'lot_id': lot1.id,
            'package_id': False,
            'result_package_id': False,
            'location_id': move2.location_id.id,
            'location_dest_id': move2.location_dest_id.id,
        })]})
        move2.action_done()

        # the first move should go back to confirmed
        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 0.0)

    def test_edit_reserved_move_line_1(self):
        """ Test that editing a stock move line linked to an untracked product correctly and
        directly adapts the reservation. In this case, we edit the sublocation where we take the
        product to another sublocation where a product is available.
        """
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, shelf1_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.product1, shelf2_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)

        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)

    def test_edit_reserved_move_line_2(self):
        """ Test that editing a stock move line linked to a tracked product correctly and directly
        adapts the reservation. In this case, we edit the lot to another available one.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product1.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product1.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 1.0)

        move1.move_line_ids.lot_id = lot2.id

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 0.0)

    def test_edit_reserved_move_line_3(self):
        """ Test that editing a stock move line linked to a packed product correctly and directly
        adapts the reservation. In this case, we edit the package to another available one.
        """
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_3'})
        package2 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_3'})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, package_id=package2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package2), 1.0)

        move1.move_line_ids.package_id = package2.id

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package2), 0.0)

    def test_edit_reserved_move_line_4(self):
        """ Test that editing a stock move line linked to an owned product correctly and directly
        adapts the reservation. In this case, we edit the owner to another available one.
        """
        owner1 = self.env['res.partner'].create({'name': 'test_edit_reserved_move_line_4_1'})
        owner2 = self.env['res.partner'].create({'name': 'test_edit_reserved_move_line_4_2'})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, owner_id=owner1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, owner_id=owner2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner2), 1.0)

        move1.move_line_ids.owner_id = owner2.id

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner2), 0.0)

    def test_edit_reserved_move_line_5(self):
        """ Test that editing a stock move line linked to a packed and tracked product correctly
        and directly adapts the reservation. In this case, we edit the lot to another available one
        that is not in a pack.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product1.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product1.id,
        })
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_5'})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot1, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 1.0)
        move_line = move1.move_line_ids[0]
        move_line.write({'package_id': False, 'lot_id': lot2.id})

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 0.0)

    def test_edit_reserved_move_line_6(self):
        """ Test that editing a stock move line linked to an untracked product correctly and
        directly adapts the reservation. In this case, we edit the sublocation where we take the
        product to another sublocation where a product is NOT available.
        """
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, shelf1_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(move1.reserved_availability, 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)

    def test_edit_reserved_move_line_7(self):
        """ Send 5 tracked products to a client, but these products do not have any lot set in our
        inventory yet: we only set them at delivery time. The created move line should have 5 items
        without any lot set, if we edit to set them to lot1, the reservation should not change.
        Validating the stock move should should not create a negative quant for this lot in stock
        location.
        # """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product3.id,
        })
        # make some stock without assigning a lot id
        self.env['stock.quant']._update_available_quantity(self.product3, self.stock_location, 5)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 5)
        move_line.qty_done = 5.0
        self.assertEqual(move_line.product_qty, 5)  # don't change reservation
        move_line.with_context(debug=True).lot_id = lot1
        self.assertEqual(move_line.product_qty, 5)  # don't change reservation when assgning a lot now

        move1.action_done()
        self.assertEqual(move_line.product_qty, 5)  # don't change reservation
        self.assertEqual(move1.state, 'done')

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product3, self.stock_location)), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product3, self.stock_location, lot_id=lot1, strict=True)), 0.0)

    def test_edit_reserved_move_line_8(self):
        """ Send 5 tracked products to a client, but some of these products do not have any lot set
        in our inventory yet: we only set them at delivery time. Adding a lot_id on the move line
        that does not have any should not change its reservation, and validating should not create
        a negative quant for this lot in stock.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product3.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product3.id,
        })
        # make some stock without assigning a lot id
        self.env['stock.quant']._update_available_quantity(self.product3, self.stock_location, 3)
        self.env['stock.quant']._update_available_quantity(self.product3, self.stock_location, 2, lot_id=lot1)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1.action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 2)

        tracked_move_line = None
        untracked_move_line = None
        for move_line in move1.move_line_ids:
            if move_line.lot_id:
                tracked_move_line = move_line
            else:
                untracked_move_line = move_line

        self.assertEqual(tracked_move_line.product_qty, 2)
        tracked_move_line.qty_done = 2

        self.assertEqual(untracked_move_line.product_qty, 3)
        untracked_move_line.lot_id = lot2
        self.assertEqual(untracked_move_line.product_qty, 3)  # don't change reservation
        untracked_move_line.qty_done = 3
        self.assertEqual(untracked_move_line.product_qty, 3)  # don't change reservation

        move1.action_done()
        self.assertEqual(untracked_move_line.product_qty, 3)  # don't change reservation
        self.assertEqual(tracked_move_line.product_qty, 2)  # don't change reservation
        self.assertEqual(move1.state, 'done')

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot2, strict=True), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product3, self.stock_location)), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product3, self.stock_location, lot_id=lot1, strict=True)), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product3, self.stock_location, lot_id=lot2, strict=True)), 0.0)

    def test_edit_done_move_line_1(self):
        """ Test that editing a done stock move line linked to an untracked product correctly and
        directly adapts the transfer. In this case, we edit the sublocation where we take the
        product to another sublocation where a product is available.
        """
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, shelf1_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.product1, shelf2_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)

        # move from shelf1
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 1
        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)

        # edit once done, we actually moved from shelf2
        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)

    def test_edit_done_move_line_2(self):
        """ Test that editing a done stock move line linked to a tracked product correctly and directly
        adapts the transfer. In this case, we edit the lot to another available one.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product1.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product1.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 1
        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 1.0)

        move1.move_line_ids.lot_id = lot2.id

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 0.0)

    def test_edit_done_move_line_3(self):
        """ Test that editing a done stock move line linked to a packed product correctly and directly
        adapts the transfer. In this case, we edit the package to another available one.
        """
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_3'})
        package2 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_3'})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, package_id=package2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 1
        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package2), 1.0)

        move1.move_line_ids.package_id = package2.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package2), 0.0)

    def test_edit_done_move_line_4(self):
        """ Test that editing a done stock move line linked to an owned product correctly and directly
        adapts the transfer. In this case, we edit the owner to another available one.
        """
        owner1 = self.env['res.partner'].create({'name': 'test_edit_reserved_move_line_4_1'})
        owner2 = self.env['res.partner'].create({'name': 'test_edit_reserved_move_line_4_2'})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, owner_id=owner1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, owner_id=owner2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 1
        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner2), 1.0)

        move1.move_line_ids.owner_id = owner2.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, owner_id=owner2), 0.0)

    def test_edit_done_move_line_5(self):
        """ Test that editing a done stock move line linked to a packed and tracked product correctly
        and directly adapts the transfer. In this case, we edit the lot to another available one
        that is not in a pack.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product1.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product1.id,
        })
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_5'})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot1, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0, lot_id=lot2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 1
        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 1.0)
        move_line = move1.move_line_ids[0]
        move_line.write({'package_id': False, 'lot_id': lot2.id})

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 0.0)

    def test_edit_done_move_line_6(self):
        """ Test that editing a done stock move line linked to an untracked product correctly and
        directly adapts the transfer. In this case, we edit the sublocation where we take the
        product to another sublocation where a product is NOT available.
        """
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, shelf1_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 1
        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), -1.0)

    def test_edit_done_move_line_7(self):
        """ Test that editing a done stock move line linked to an untracked product correctly and
        directly adapts the transfer. In this case, we edit the sublocation where we take the
        product to another sublocation where a product is NOT available because it has been reserved
        by another move.
        """
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, shelf1_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.product1, shelf2_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 1
        move1.action_done()

        move2 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2.action_confirm()
        move2.action_assign()

        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)
        self.assertEqual(move2.state, 'confirmed')

    def test_edit_done_move_line_8(self):
        """ Test that editing a done stock move line linked to an untracked product correctly and
        directly adapts the transfer. In this case, we increment the quantity done (and we do not
        have more in stock.
        """
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, shelf1_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)

        # move from shelf1
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 1
        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        # edit once done, we actually moved 2 products
        move1.move_line_ids.qty_done = 2

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), -1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), -1.0)

    def test_edit_done_move_line_9(self):
        """ Test that editing a done stock move line linked to an untracked product correctly and
        directly adapts the transfer. In this case, we "cancel" the move by zeroing the qty done.
        """
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, shelf1_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)

        # move from shelf1
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 1
        move1.action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        # edit once done, we actually moved 2 products
        move1.move_line_ids.qty_done = 0

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)

    def test_edit_done_move_line_10(self):
        """ Edit the quantity done for an incoming move shoudld also remove the quant if there
            are no product in stock.
        """
        # move from shelf1
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 10
        move1.action_done()

        quant = self.env['stock.quant']._gather(self.product1, self.stock_location)
        self.assertEqual(len(quant), 1.0)

        # edit once done, we actually moved 2 products
        move1.move_line_ids.qty_done = 0

        quant = self.env['stock.quant']._gather(self.product1, self.stock_location)
        self.assertEqual(len(quant), 0.0)

    def test_edit_done_move_line_11(self):
        """ Add a move line and check if the quant is updated
        """
        owner = self.env['res.partner'].create({'name': 'Jean'})
        picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': owner.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        # move from shelf1
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_id': picking.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.action_assign()
        move1.move_line_ids.qty_done = 10
        picking.action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 10.0)
        self.env['stock.move.line'].create({
            'picking_id': move1.move_line_ids.picking_id.id,
            'move_id': move1.move_line_ids.move_id.id,
            'product_id': move1.move_line_ids.product_id.id,
            'qty_done': move1.move_line_ids.qty_done,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.move_line_ids.location_id.id,
            'location_dest_id': move1.move_line_ids.location_dest_id.id,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 20.0)
        move1.move_line_ids[1].qty_done = 5
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 15.0)

    def test_immediate_validate_1(self):
        """ Create a picking and simulates validate button effect.
            Move line quantity should be set to their reservation quantity automatically
        """
        owner = self.env['res.partner'].create({'name': 'Jean'})
        picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': owner.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        # move from shelf1
        self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_id': picking.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.action_assign()
        res_dict = picking.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 10.0)

    def test_immediate_validate_2(self):
        """ Create a picking and simulates validate button effect.
            Move line quantity should be set to their reservation quantity automatically.
            If the Initial demand quantity is greater than the available quantity. It should only
            set the quantity done to the available(reserved) quantity and create a backorder with the
            remaining quantity.
        """
        owner = self.env['res.partner'].create({'name': 'Jean'})
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 5.0)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': owner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        # move from shelf1
        self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_id': picking.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.action_assign()
        res_dict = picking.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        self.assertEqual(len(picking.move_lines.move_line_ids), 1)
        self.assertEqual(picking.move_lines.quantity_done, 5.0)
        self.assertEqual(picking.move_lines.move_line_ids.qty_done, 5.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 0.0)

        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
        self.assertEqual(len(backorder), 1.0)
        self.assertEqual(backorder.move_lines.product_uom_qty, 5.0)

    def test_immediate_validate_3(self):
        """ Create a picking and simulates validate button effect.
            In case of a force assign it should ignore the reserved quantity and set
            the quantity done to the initial demand. It should also create the move line.
        """
        owner = self.env['res.partner'].create({'name': 'Jean'})
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': owner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        # move from shelf1
        self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_id': picking.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.force_assign()
        res_dict = picking.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        self.assertEqual(picking.move_lines.quantity_done, 10.0)
        # Check move_lines data
        self.assertEqual(len(picking.move_lines.move_line_ids), 1)
        self.assertEqual(picking.move_lines.move_line_ids.qty_done, 10.0)
        self.assertEqual(picking.move_lines.move_line_ids.product_qty, 0.0)
        # Check quants data
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), -10.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)

    def test_immediate_validate_4(self):
        """ Create a picking and simulates validate button effect.
            If the product is tracked by lot. The user should set the lot
            and the quantity done himself before validate. Otherwise it should
            return a UserError.
        """
        owner = self.env['res.partner'].create({'name': 'Jean'})
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product3.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product3, self.stock_location, 5.0, lot_id=lot1)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': owner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        # move from shelf1
        self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_id': picking.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        picking.action_confirm()
        picking.action_assign()
        with self.assertRaises(UserError):
            picking.button_validate()
        picking.move_lines.move_line_ids[0].qty_done = 5.0
        # We do not need to catch wizard since everything is already defined and the action_done will be processed immediately
        picking.button_validate()

        self.assertEqual(picking.move_lines.quantity_done, 5.0)
        # Check move_lines data
        self.assertEqual(len(picking.move_lines.move_line_ids), 1)
        self.assertEqual(picking.move_lines.move_line_ids.lot_id, lot1)
        self.assertEqual(picking.move_lines.move_line_ids.qty_done, 5.0)
        # Check quants data
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 0.0)

    def test_set_quantity_done_1(self):
        move1 = self.env['stock.move'].create({
            'name': 'test_set_quantity_done_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_set_quantity_done_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        (move1 + move2).action_confirm()
        (move1 + move2).force_assign()
        (move1 + move2).write({'quantity_done': 1})
        self.assertEqual(move1.quantity_done, 1)
        self.assertEqual(move2.quantity_done, 1)

    def test_initial_demand_1(self):
        """ Check that the initial demand is set to 0 when creating a move by hand, and
        that changing the product on the move do not reset the initial demand.
        """
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
        })
        self.assertEqual(move1.state, 'draft')
        self.assertEqual(move1.product_uom_qty, 0)
        move1.product_uom_qty = 100
        move1.product_id = self.product2
        move1.onchange_product_id()
        self.assertEqual(move1.product_uom_qty, 100)

    def test_scrap_1(self):
        """ Check the created stock move and the impact on quants when we scrap a
        stockable product.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1)
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product1.id,
            'product_uom_id':self.product1.uom_id.id,
            'scrap_qty': 1,
        })
        self.assertEqual(scrap.state, 'done')
        move = scrap.move_id
        self.assertEqual(move.state, 'done')
        self.assertEqual(move.quantity_done, 1)
        self.assertEqual(move.scrapped, True)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0)

    def test_scrap_2(self):
        """ Check the created stock move and the impact on quants when we scrap a
        consumable product.
        """
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product4.id,
            'product_uom_id':self.product4.uom_id.id,
            'scrap_qty': 1,
        })
        self.assertEqual(scrap.state, 'done')
        move = scrap.move_id
        self.assertEqual(move.state, 'done')
        self.assertEqual(move.quantity_done, 1)
        self.assertEqual(move.scrapped, True)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product4, self.stock_location), 0)

    def test_scrap_3(self):
        """ Scrap the product of a reserved move line. Check that the move line is
        correctly deleted and that the associated stock move is not assigned anymore.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1)
        move1 = self.env['stock.move'].create({
            'name': 'test_set_quantity_done_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1.action_confirm()
        move1.action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        scrap = self.env['stock.scrap'].create({
            'product_id': self.product1.id,
            'product_uom_id':self.product1.uom_id.id,
            'scrap_qty': 1,
        })

        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(len(move1.move_line_ids), 0)
