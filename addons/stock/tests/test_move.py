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
        self.pack_location.active = True
        self.transit_location = self.env['stock.location'].search([
            ('company_id', '=', self.env.user.company_id.id),
            ('usage', '=', 'transit'),
        ], limit=1)
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.uom_dozen = self.env.ref('uom.product_uom_dozen')
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

    def gather_relevant(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        quants = self.env['stock.quant']._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        return quants.filtered(lambda q: not (q.quantity == 0 and q.reserved_quantity == 0))

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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # fill the move line
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 100.0)
        self.assertEqual(move_line.qty_done, 0.0)
        move_line.qty_done = 100.0

        # validation
        move1._action_done()
        self.assertEqual(move1.state, 'done')
        # no quants are created in the supplier location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.supplier_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.supplier_location, allow_negative=True), -100.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 100.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.supplier_location)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)

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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 5)
        move_line.lot_name = 'lot1'
        move_line.qty_done = 5.0
        self.assertEqual(move_line.product_qty, 5)  # don't change reservation

        move1._action_done()
        self.assertEqual(move_line.product_qty, 0)  # change reservation to 0 for done move
        self.assertEqual(move1.state, 'done')

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.supplier_location), 0.0)
        supplier_quants = self.gather_relevant(self.product3, self.supplier_location)
        self.assertEqual(sum(supplier_quants.mapped('quantity')), -5.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location), 5.0)
        self.assertEqual(len(self.gather_relevant(self.product3, self.supplier_location)), 1.0)
        quants = self.gather_relevant(self.product3, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        for quant in quants:
            self.assertNotEqual(quant.in_date, False)

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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
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

        move1._action_done()

        self.assertEqual(move1.quantity_done, 5.0)
        self.assertEqual(move1.product_qty, 5)  # don't change reservation
        self.assertEqual(move1.state, 'done')

        # Quant balance should result with 5 quant in supplier and stock
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.supplier_location), 0.0)
        supplier_quants = self.gather_relevant(self.product2, self.supplier_location)
        self.assertEqual(sum(supplier_quants.mapped('quantity')), -5.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 5.0)

        self.assertEqual(len(self.gather_relevant(self.product2, self.supplier_location)), 5.0)
        quants = self.gather_relevant(self.product2, self.stock_location)
        self.assertEqual(len(quants), 5.0)
        for quant in quants:
            self.assertNotEqual(quant.in_date, False)

    def test_out_1(self):
        """ Send products to a client. Check that a move line is created reserving products in
        stock and that the delivery correctly remove the single quant in stock.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 100)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)
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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        # Should be a reserved quantity and thus a quant.
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)

        # fill the move line
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 100.0)
        self.assertEqual(move_line.qty_done, 0.0)
        move_line.qty_done = 100.0

        # validation
        move1._action_done()
        self.assertEqual(move1.state, 'done')
        # Check there is one quant in customer location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.customer_location), 100.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.customer_location)), 1.0)
        # there should be no quant amymore in the stock location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 0.0)

    def test_out_2(self):
        """ Send a consumable product to a client. Check that a move line is created but
            quants are not impacted.
        """
        # make some stock

        self.product1.type = 'consu'
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 0.0)
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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        # Should be a reserved quantity and thus a quant.
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 0.0)

        # fill the move line
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 100.0)
        self.assertEqual(move_line.qty_done, 0.0)
        move_line.qty_done = 100.0

        # validation
        move1._action_done()
        self.assertEqual(move1.state, 'done')
        # no quants are created in the customer location since it's a consumable
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.customer_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.customer_location)), 0.0)
        # there should be no quant amymore in the stock location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 0.0)

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
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(len(move1.move_line_ids), 2)

    def test_mixed_tracking_reservation_2(self):
        """ Send products tracked by lot to a customer. In your stock, there are two tracked and
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
        move1._action_confirm()
        move1._action_assign()
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
        self.assertEqual(len(self.gather_relevant(self.product2, self.stock_location, strict=True)), 1.0)  # with a qty of 2
        self.assertEqual(len(self.gather_relevant(self.product2, self.stock_location, lot_id=lot1, strict=True)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product2, self.stock_location, lot_id=lot2, strict=True)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product2, self.stock_location, lot_id=lot3, strict=True)), 0)
        self.assertEqual(len(self.gather_relevant(self.product2, self.stock_location, lot_id=lot4, strict=True)), 0)

        move1.move_line_ids.write({'qty_done': 1.0})

        move1._action_done()

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.write({'qty_done': 1.0})
        move1._action_done()

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.write({'qty_done': 1.0})
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot2, strict=True), 0.0)

        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1)
        lot3 = self.env['stock.production.lot'].create({
            'name': 'lot3',
            'product_id': self.product2.id,
        })

        move1.move_line_ids[1].lot_id = lot3

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
        move1._action_confirm()
        move1._action_assign()
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
        move1._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product2, self.stock_location)), 0.0)

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
        move1._action_confirm()
        move1._action_assign()
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
        move1._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product2, self.stock_location)), 0.0)

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
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(len(move1.move_line_ids), 2)
        for ml in move1.move_line_ids:
            self.assertEqual(ml.product_qty, 1.0)

        untracked_move_line = move1.move_line_ids.filtered(lambda ml: not ml.lot_id).lot_id = lot2
        for ml in move1.move_line_ids:
            self.assertEqual(ml.product_qty, 1.0)

        move1.move_line_ids.write({'qty_done': 1.0})

        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot2, strict=True), 0.0)
        quants = self.gather_relevant(self.product2, self.stock_location)
        self.assertEqual(len(quants), 0)

    def test_mixed_tracking_reservation_8(self):
        """ Send one product tracked by lot to a customer. In your stock, there are one tracked and
        one untracked quant. Reserve the move, then edit the lot to one not present in stock. The
        system will update the reservation and use the untracked quant. Now unreserve, no error
        should happen
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product2.id,
        })

        # at first, we only make the tracked quant available in stock to make sure this one is selected
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1, lot_id=lot1)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_mixed_tracking_reservation_7',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(move1.move_line_ids.lot_id.id, lot1.id)

        # change the lot_id to one not available in stock while an untracked quant is available
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1)
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product2.id,
        })
        move1.move_line_ids.lot_id = lot2
        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(move1.move_line_ids.lot_id.id, lot2.id)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 1.0)

        # unreserve
        move1._do_unreserve()

        self.assertEqual(move1.reserved_availability, 0.0)
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 1.0)

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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf1_location.id)

    def test_putaway_2(self):
        """ Receive products from a supplier. Check that putaway rules are rightly applied on
        the receipt move line.
        """
        # This test will apply a putaway strategy by product on the stock location to put everything
        # incoming in the sublocation shelf1.
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        putaway = self.env['product.putaway'].create({
            'name': 'putaway stock->shelf1',
            'product_location_ids': [(0, 0, {
                'product_id': self.env.ref('product.product_product_5').id,
                'fixed_location_id': shelf1_location.id,
            })]
        })
        self.stock_location.write({
            'putaway_strategy_id': putaway.id,
        })

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.env.ref('product.product_product_5').id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf1_location.id)

    def test_putaway_3(self):
        """ Receive products from a supplier. Check that putaway rules are rightly applied on
        the receipt move line.
        """
        # This test will apply both the putaway strategy by product and category. We check here
        # that the putaway by product takes precedence.

        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        putaway = self.env['product.putaway'].create({
            'name': 'putaway stock->shelf1',
            'fixed_location_ids': [(0, 0, {
                'category_id': self.env.ref('product.product_category_all').id,
                'fixed_location_id': shelf1_location.id,
            })],
            'product_location_ids': [(0, 0, {
                'product_id': self.env.ref('stock.product_cable_management_box').id,
                'fixed_location_id': shelf2_location.id,
            })],
        })
        self.stock_location.write({
            'putaway_strategy_id': putaway.id,
        })

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_3',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.env.ref('stock.product_cable_management_box').id,
            'product_uom': self.env.ref('uom.product_uom_kgm').id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf2_location.id)

    def test_putaway_4(self):
        """ Receive products from a supplier. Check that putaway rules are rightly applied on
        the receipt move line.
        """
        # This test will apply both the putaway strategy by product and category. We check here
        # that if a putaway by product is not matched, the fallback to the category is correctly
        # done.

        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        putaway = self.env['product.putaway'].create({
            'name': 'putaway stock->shelf1',
            'fixed_location_ids': [(0, 0, {
                'category_id': self.env.ref('product.product_category_all').id,
                'fixed_location_id': shelf1_location.id,
            })],
            'product_location_ids': [(0, 0, {
                'product_id': self.env.ref('stock.product_cable_management_box').id,
                'fixed_location_id': shelf2_location.id,
            })],
        })
        self.stock_location.write({
            'putaway_strategy_id': putaway.id,
        })

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_4',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
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
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 150.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)
        self.assertEqual(move1.availability, 100.0)

    def test_availability_2(self):
        """ Check that the `availability` field on a move is correctly computed when there is
        not enough products in stock.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 50.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 50.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)
        self.assertEqual(move1.availability, 50.0)

    def test_availability_3(self):
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product2.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product2.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, -1.0, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1.0, lot_id=lot2)
        move1 = self.env['stock.move'].create({
            'name': 'test_availability_3',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move1.reserved_availability, 1.0)

    def test_availability_4(self):
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 30.0)
        move1 = self.env['stock.move'].create({
            'name': 'test_availability_4',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')

        move2 = self.env['stock.move'].create({
            'name': 'test_availability_4',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
        })
        move2._action_confirm()
        move2._action_assign()

        # set 15 as quantity done for the first and 30 as the second
        move1.move_line_ids.qty_done = 15
        move2.move_line_ids.qty_done = 30

        # validate the second, the first should be unreserved
        move2._action_done()

        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(move1.move_line_ids.qty_done, 15)
        self.assertEqual(move2.state, 'done')

        stock_quants = self.gather_relevant(self.product1, self.stock_location)
        self.assertEqual(len(stock_quants), 0)
        customer_quants = self.gather_relevant(self.product1, self.customer_location)
        self.assertEqual(customer_quants.quantity, 30)
        self.assertEqual(customer_quants.reserved_quantity, 0)

    def test_availability_5(self):
        """ Check that rerun action assign only create new stock move
        lines instead of adding quantity in existing one.
        """
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 2.0)
        # move from shelf1
        move = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4.0,
        })
        move._action_confirm()
        move._action_assign()

        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 4.0)
        move._action_assign()

        self.assertEqual(len(move.move_line_ids), 4.0)

    def test_availability_6(self):
        """ Check that, in the scenario where a move is in a bigger uom than the uom of the quants
        and this uom only allows entire numbers, we don't make a partial reservation when the
        quantity available is not enough to reserve the move. Check also that it is not possible
        to set `quantity_done` with a value not honouring the UOM's rounding.
        """
        # on the dozen uom, set the rounding set 1.0
        self.uom_dozen.rounding = 1

        # 6 units are available in stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 6.0)

        # the move should not be reserved
        move = self.env['stock.move'].create({
            'name': 'test_availability_6',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1,
        })
        move._action_confirm()
        move._action_assign()
        self.assertEqual(move.state, 'confirmed')

        # the quants should be left untouched
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 6.0)

        # make 8 units available, the move should again not be reservabale
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2.0)
        move._action_assign()
        self.assertEqual(move.state, 'confirmed')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 8.0)

        # make 12 units available, this time the move should be reservable
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4.0)
        move._action_assign()
        self.assertEqual(move.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        # Check it isn't possible to set any value to quantity_done
        with self.assertRaises(UserError):
            move.quantity_done = 0.1
            move._action_done()

        with self.assertRaises(UserError):
            move.quantity_done = 1.1
            move._action_done()

        with self.assertRaises(UserError):
            move.quantity_done = 0.9
            move._action_done()

        move.quantity_done = 1
        move._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.customer_location), 12.0)

    def test_availability_7(self):
        """ Check that, in the scenario where a move is in a bigger uom than the uom of the quants
        and this uom only allows entire numbers, we only reserve quantity honouring the uom's
        rounding even if the quantity is set across multiple quants.
        """
        # on the dozen uom, set the rounding set 1.0
        self.uom_dozen.rounding = 1

        # make 12 quants of 1
        for i in range(1, 13):
            lot_id = self.env['stock.production.lot'].create({
                'name': 'lot%s' % str(i),
                'product_id': self.product2.id,
            })
            self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1.0, lot_id=lot_id)

        # the move should be reserved
        move = self.env['stock.move'].create({
            'name': 'test_availability_7',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1,
        })
        move._action_confirm()
        move._action_assign()
        self.assertEqual(move.state, 'assigned')
        self.assertEqual(len(move.move_line_ids.mapped('product_uom_id')), 1)
        self.assertEqual(move.move_line_ids.mapped('product_uom_id'), self.uom_unit)

        for move_line in move.move_line_ids:
            move_line.qty_done = 1
        move._action_done()

        self.assertEqual(move.product_uom_qty, 1)
        self.assertEqual(move.product_uom.id, self.uom_dozen.id)
        self.assertEqual(move.state, 'done')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.customer_location), 12.0)
        self.assertEqual(len(self.gather_relevant(self.product2, self.customer_location)), 12)

    def test_availability_8(self):
        """ Test the assignment mechanism when the product quantity is decreased on a partially
            reserved stock move.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 3.0)
        self.assertAlmostEqual(self.product1.qty_available, 3.0)

        move_partial = self.env['stock.move'].create({
            'name': 'test_partial',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })

        move_partial._action_confirm()
        move_partial._action_assign()
        self.assertAlmostEqual(self.product1.virtual_available, -2.0)
        self.assertEqual(move_partial.state, 'partially_available')
        move_partial.product_uom_qty = 3.0
        move_partial._action_assign()
        self.assertEqual(move_partial.state, 'assigned')

    def test_availability_9(self):
        """ Test the assignment mechanism when the product quantity is increase
        on a receipt move.
        """
        move_receipt = self.env['stock.move'].create({
            'name': 'test_receipt_edit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1.0,
        })

        move_receipt._action_confirm()
        move_receipt._action_assign()
        self.assertEqual(move_receipt.state, 'assigned')
        move_receipt.product_uom_qty = 3.0
        move_receipt._action_assign()
        self.assertEqual(move_receipt.state, 'assigned')
        self.assertEqual(move_receipt.move_line_ids.product_uom_qty, 3)

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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 50.0)

        # unreserve
        move1._do_unreserve()
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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 50.0)

        # unreserve
        move1._do_unreserve()
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=package1), 150.0)
        self.assertEqual(move1.state, 'confirmed')

    def test_unreserve_3(self):
        """ Similar to `test_unreserve_1` but checking the quants more in details.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)
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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        quants = self.gather_relevant(self.product1, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 2.0)

        move1._do_unreserve()
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
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)
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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'partially_available')
        self.assertEqual(len(move1.move_line_ids), 1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        quants = self.gather_relevant(self.product1, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 2.0)

        move1._do_unreserve()
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
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 2)
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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        move1._do_unreserve()

        quants = self.gather_relevant(self.product1, self.stock_location)
        self.assertEqual(len(quants), 2.0)
        for quant in quants:
            self.assertEqual(quant.reserved_quantity, 0)

    def test_unreserve_6(self):
        """ In a situation with a negative and a positive quant, reserve and unreserve.
        """
        q1 = self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
            'quantity': -10,
            'reserved_quantity': 0,
        })

        q2 = self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
            'quantity': 30.0,
            'reserved_quantity': 10.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 10.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_unreserve_6',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.product_qty, 10)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(q2.reserved_quantity, 20)

        move1._do_unreserve()
        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 10.0)
        self.assertEqual(q2.reserved_quantity, 10)

    def test_link_assign_1(self):
        """ Test the assignment mechanism when two chained stock moves try to move one unit of an
        untracked product.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)

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

        (move_stock_pack + move_pack_cust)._action_confirm()
        move_stock_pack._action_assign()
        move_stock_pack.move_line_ids[0].qty_done = 1.0
        move_stock_pack._action_done()
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
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location, lot1)), 1.0)

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

        (move_stock_pack + move_pack_cust)._action_confirm()
        move_stock_pack._action_assign()

        move_line_stock_pack = move_stock_pack.move_line_ids[0]
        self.assertEqual(move_line_stock_pack.lot_id.id, lot1.id)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location, lot1)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.pack_location, lot1)), 0.0)

        move_line_stock_pack.qty_done = 1.0
        move_stock_pack._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location, lot1)), 0.0)

        move_line_pack_cust = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line_pack_cust.lot_id.id, lot1.id)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.pack_location, lot_id=lot1), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.pack_location, lot1)), 1.0)

    def test_link_assign_3(self):
        """ Test the assignment mechanism when three chained stock moves (2 sources, 1 dest) try to
        move multiple units of an untracked product.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)

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
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack_1.id, 0), (4, move_stock_pack_2.id, 0)]})

        (move_stock_pack_1 + move_stock_pack_2 + move_pack_cust)._action_confirm()

        # assign and fulfill the first move
        move_stock_pack_1._action_assign()
        self.assertEqual(move_stock_pack_1.state, 'assigned')
        self.assertEqual(len(move_stock_pack_1.move_line_ids), 1)
        move_stock_pack_1.move_line_ids[0].qty_done = 1.0
        move_stock_pack_1._action_done()
        self.assertEqual(move_stock_pack_1.state, 'done')

        # the destination move should be partially available and have one move line
        self.assertEqual(move_pack_cust.state, 'partially_available')
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)
        # Should have 1 quant in stock_location and another in pack_location
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.pack_location)), 1.0)

        move_stock_pack_2._action_assign()
        self.assertEqual(move_stock_pack_2.state, 'assigned')
        self.assertEqual(len(move_stock_pack_2.move_line_ids), 1)
        move_stock_pack_2.move_line_ids[0].qty_done = 1.0
        move_stock_pack_2._action_done()
        self.assertEqual(move_stock_pack_2.state, 'done')

        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.pack_location)), 1.0)

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
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location, lot1)), 1.0)

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
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack_1.id, 0), (4, move_stock_pack_2.id, 0)]})

        (move_stock_pack_1 + move_stock_pack_2 + move_pack_cust)._action_confirm()

        # assign and fulfill the first move
        move_stock_pack_1._action_assign()
        self.assertEqual(len(move_stock_pack_1.move_line_ids), 1)
        self.assertEqual(move_stock_pack_1.move_line_ids[0].lot_id.id, lot1.id)
        move_stock_pack_1.move_line_ids[0].qty_done = 1.0
        move_stock_pack_1._action_done()

        # the destination move should be partially available and have one move line
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)

        move_stock_pack_2._action_assign()
        self.assertEqual(len(move_stock_pack_2.move_line_ids), 1)
        self.assertEqual(move_stock_pack_2.move_line_ids[0].lot_id.id, lot1.id)
        move_stock_pack_2.move_line_ids[0].qty_done = 1.0
        move_stock_pack_2._action_done()

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
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust_1.id, 0), (4, move_pack_cust_2.id, 0)]})
        move_pack_cust_1.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})
        move_pack_cust_2.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust_1 + move_pack_cust_2)._action_confirm()

        # assign and fulfill the first move
        move_stock_pack._action_assign()
        self.assertEqual(len(move_stock_pack.move_line_ids), 1)
        move_stock_pack.move_line_ids[0].qty_done = 2.0
        move_stock_pack._action_done()

        # the destination moves should be available and have one move line
        self.assertEqual(len(move_pack_cust_1.move_line_ids), 1)
        self.assertEqual(len(move_pack_cust_2.move_line_ids), 1)

        move_pack_cust_1.move_line_ids[0].qty_done = 1.0
        move_pack_cust_2.move_line_ids[0].qty_done = 1.0
        (move_pack_cust_1 + move_pack_cust_2)._action_done()

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
        move_stock_stock_1.write({'move_orig_ids': [(4, move_supp_stock_1.id, 0), (4, move_supp_stock_2.id, 0)]})
        move_stock_stock_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_6_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move_stock_stock_2.write({'move_orig_ids': [(4, move_supp_stock_1.id, 0), (4, move_supp_stock_2.id, 0)]})

        (move_supp_stock_1 + move_supp_stock_2 + move_stock_stock_1 + move_stock_stock_2)._action_confirm()
        move_supp_stock_1._action_assign()
        self.assertEqual(move_supp_stock_1.state, 'assigned')
        self.assertEqual(move_supp_stock_2.state, 'confirmed')
        self.assertEqual(move_stock_stock_1.state, 'waiting')
        self.assertEqual(move_stock_stock_2.state, 'waiting')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        # do the fist move, it'll bring 3 units in stock location so only `move_stock_stock_1`
        # should be assigned
        move_supp_stock_1.move_line_ids.qty_done = 3.0
        move_supp_stock_1._action_done()
        self.assertEqual(move_supp_stock_1.state, 'done')
        self.assertEqual(move_supp_stock_2.state, 'confirmed')
        self.assertEqual(move_stock_stock_1.state, 'assigned')
        self.assertEqual(move_stock_stock_2.state, 'waiting')

    def test_link_assign_7(self):
        # on the dozen uom, set the rounding set 1.0
        self.uom_dozen.rounding = 1

        # 6 units are available in stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 6.0)

        # create pickings and moves for a pick -> pack mto scenario
        picking_stock_pack = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
        })
        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_7',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1.0,
            'picking_id': picking_stock_pack.id,
        })
        picking_pack_cust = self.env['stock.picking'].create({
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_7',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1.0,
            'picking_id': picking_pack_cust.id,
        })
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})
        (move_stock_pack + move_pack_cust)._action_confirm()

        # the pick should not be reservable because of the rounding of the dozen
        move_stock_pack._action_assign()
        self.assertEqual(move_stock_pack.state, 'confirmed')
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, 'waiting')

        # move the 6 units by adding an unreserved move line
        move_stock_pack.write({'move_line_ids': [(0, 0, {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'qty_done': 6,
            'product_uom_qty': 0,
            'lot_id': False,
            'package_id': False,
            'result_package_id': False,
            'location_id': move_stock_pack.location_id.id,
            'location_dest_id': move_stock_pack.location_dest_id.id,
            'picking_id': picking_stock_pack.id,
        })]})

        # the quantity done on the move should not respect the rounding of the move line
        self.assertEqual(move_stock_pack.quantity_done, 0.5)

        # create the backorder in the uom of the quants
        backorder_wizard_dict = picking_stock_pack.button_validate()
        backorder_wizard = self.env[backorder_wizard_dict['res_model']].browse(backorder_wizard_dict['res_id'])
        backorder_wizard.process()
        self.assertEqual(move_stock_pack.state, 'done')
        self.assertEqual(move_stock_pack.quantity_done, 0.5)
        self.assertEqual(move_stock_pack.product_uom_qty, 0.5)

        # the second move should not be reservable because of the rounding on the dozen
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, 'partially_available')
        move_line_pack_cust = move_pack_cust.move_line_ids
        self.assertEqual(move_line_pack_cust.product_uom_qty, 6)
        self.assertEqual(move_line_pack_cust.product_uom_id.id, self.uom_unit.id)

        # move a dozen on the backorder to see how we handle the extra move
        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking_stock_pack.id)])
        backorder.move_lines.write({'move_line_ids': [(0, 0, {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_dozen.id,
            'qty_done': 1,
            'product_uom_qty': 0,
            'lot_id': False,
            'package_id': False,
            'result_package_id': False,
            'location_id': backorder.location_id.id,
            'location_dest_id': backorder.location_dest_id.id,
            'picking_id': backorder.id,
        })]})
        overprocessed_wizard_dict = backorder.button_validate()
        overprocessed_wizard = self.env[overprocessed_wizard_dict['res_model']].browse(overprocessed_wizard_dict['res_id'])
        overprocessed_wizard.action_confirm()
        backorder_move = backorder.move_lines
        self.assertEqual(backorder_move.state, 'done')
        self.assertEqual(backorder_move.quantity_done, 12.0)
        self.assertEqual(backorder_move.product_uom_qty, 12.0)
        self.assertEqual(backorder_move.product_uom, self.uom_unit)

        # the second move should now be reservable
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, 'assigned')
        self.assertEqual(move_line_pack_cust.product_uom_qty, 12)
        self.assertEqual(move_line_pack_cust.product_uom_id.id, self.uom_unit.id)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, move_stock_pack.location_dest_id), 6)

    def test_link_assign_8(self):
        """ Set the rounding of the dozen to 1.0, create a chain of two move for a dozen, the product
        concerned is tracked by serial number. Check that the flow is ok.
        """
        # on the dozen uom, set the rounding set 1.0
        self.uom_dozen.rounding = 1

        # 6 units are available in stock
        for i in range(1, 13):
            lot_id = self.env['stock.production.lot'].create({
                'name': 'lot%s' % str(i),
                'product_id': self.product2.id,
            })
            self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1.0, lot_id=lot_id)

        # create pickings and moves for a pick -> pack mto scenario
        picking_stock_pack = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
        })
        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_7',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1.0,
            'picking_id': picking_stock_pack.id,
        })
        picking_pack_cust = self.env['stock.picking'].create({
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_7',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1.0,
            'picking_id': picking_pack_cust.id,
        })
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})
        (move_stock_pack + move_pack_cust)._action_confirm()

        move_stock_pack._action_assign()
        self.assertEqual(move_stock_pack.state, 'assigned')
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, 'waiting')

        for ml in move_stock_pack.move_line_ids:
            ml.qty_done = 1
        picking_stock_pack.button_validate()
        self.assertEqual(move_pack_cust.state, 'assigned')
        for ml in move_pack_cust.move_line_ids:
            self.assertEqual(ml.product_uom_qty, 1)
            self.assertEqual(ml.product_uom_id.id, self.uom_unit.id)
            self.assertTrue(bool(ml.lot_id.id))

    def test_link_assign_9(self):
        """ Create an uom "3 units" which is 3 times the units but without rounding. Create 3
        quants in stock and two chained moves. The first move will bring the 3 quants but the
        second only validate 2 and create a backorder for the last one. Check that the reservation
        is correctly cleared up for the last one.
        """
        uom_3units = self.env['uom.uom'].create({
            'name': '3 units',
            'category_id': self.uom_unit.category_id.id,
            'factor_inv': 3,
            'rounding': 1,
            'uom_type': 'bigger',
        })
        for i in range(1, 4):
            lot_id = self.env['stock.production.lot'].create({
                'name': 'lot%s' % str(i),
                'product_id': self.product2.id,
            })
            self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1.0, lot_id=lot_id)

        picking_stock_pack = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
        })
        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_9',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product2.id,
            'product_uom': uom_3units.id,
            'product_uom_qty': 1.0,
            'picking_id': picking_stock_pack.id,
        })
        picking_pack_cust = self.env['stock.picking'].create({
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_0',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': uom_3units.id,
            'product_uom_qty': 1.0,
            'picking_id': picking_pack_cust.id,
        })
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})
        (move_stock_pack + move_pack_cust)._action_confirm()

        picking_stock_pack.action_assign()
        for ml in picking_stock_pack.move_lines.move_line_ids:
            ml.qty_done = 1
        picking_stock_pack.button_validate()
        self.assertEqual(picking_pack_cust.state, 'assigned')
        for ml in picking_pack_cust.move_lines.move_line_ids:
            if ml.lot_id.name != 'lot3':
                ml.qty_done = 1
        res_dict_for_back_order = picking_pack_cust.button_validate()
        backorder_wizard = self.env[(res_dict_for_back_order.get('res_model'))].browse(res_dict_for_back_order.get('res_id'))
        backorder_wizard.process()
        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking_pack_cust.id)])
        backordered_move = backorder.move_lines

        # due to the rounding, the backordered quantity is 0.999 ; we shoudln't be able to reserve
        # 0.999 on a tracked by serial number quant
        backordered_move._action_assign()
        self.assertEqual(backordered_move.reserved_availability, 0)

        # force the serial number and validate
        lot3 = self.env['stock.production.lot'].search([('name', '=', "lot3")])
        backorder.write({'move_line_ids': [(0, 0, {
            'product_id': self.product2.id,
            'product_uom_id': self.uom_unit.id,
            'qty_done': 1,
            'product_uom_qty': 0,
            'lot_id': lot3.id,
            'package_id': False,
            'result_package_id': False,
            'location_id': backordered_move.location_id.id,
            'location_dest_id': backordered_move.location_dest_id.id,
            'move_id': backordered_move.id,
        })]})

        overprocessed_wizard = backorder.button_validate()
        overprocessed_wizard = self.env['stock.overprocessed.transfer'].browse(overprocessed_wizard['res_id'])
        overprocessed_wizard.action_confirm()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.customer_location), 3)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.pack_location), 0)

    def test_link_assign_10(self):
        """ Test the assignment mechanism with partial availability.
        """
        # make some stock:
        #   stock location: 2.0
        #   pack location: -1.0
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 1.0)

        move_out = self.env['stock.move'].create({
            'name': 'test_link_assign_out',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_out._action_confirm()
        move_out._action_assign()
        move_out.quantity_done = 1.0
        move_out._action_done()
        self.assertEqual(len(self.gather_relevant(self.product1, self.pack_location)), 1.0)

        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust)._action_confirm()
        move_stock_pack._action_assign()
        move_stock_pack.quantity_done = 2.0
        move_stock_pack._action_done()
        self.assertEqual(len(move_pack_cust.move_line_ids), 1)

        self.assertAlmostEqual(move_pack_cust.reserved_availability, 1.0)
        self.assertEqual(move_pack_cust.state, 'partially_available')

    def test_use_reserved_move_line_1(self):
        """ Test that _free_reservation work when quantity is only available on
        reserved move lines.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 10.0)
        move1 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move2._action_confirm()
        move2._action_assign()
        move3 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 0.0,
            'quantity_done': 1.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3._action_done()
        self.assertEqual(move3.state, 'done')
        quant = self.env['stock.quant']._gather(self.product1, self.stock_location)
        self.assertEqual(quant.quantity, 9.0)
        self.assertEqual(quant.reserved_quantity, 9.0)

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
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        move2._action_confirm()
        move2._action_assign()
        self.assertEqual(move2.state, 'confirmed')

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
        move2._action_done()

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
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        move2._action_confirm()
        move2._action_assign()
        self.assertEqual(move2.state, 'confirmed')

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
        move2._action_done()

        # the first move should go back to confirmed
        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 0.0)

    def test_use_unreserved_move_line_3(self):
        """ Test the behavior of `_free_reservation` when ran on a recordset of move lines where
        some are assigned and some are force assigned. `_free_reservation` should not use an
        already processed move line when looking for a move line candidate to unreserve.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_3',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.quantity_done = 1

        # add a forced move line in `move1`
        move1.write({'move_line_ids': [(0, 0, {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'qty_done': 2,
            'product_uom_qty': 0,
            'lot_id': False,
            'package_id': False,
            'result_package_id': False,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
        })]})
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.customer_location), 3.0)

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
        move1._action_confirm()
        move1._action_assign()

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
        move1._action_confirm()
        move1._action_assign()

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
        move1._action_confirm()
        move1._action_assign()

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
        move1._action_confirm()
        move1._action_assign()

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
        move1._action_confirm()
        move1._action_assign()

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
        move1._action_confirm()
        move1._action_assign()

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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 5)
        move_line.qty_done = 5.0
        self.assertEqual(move_line.product_qty, 5)  # don't change reservation
        move_line.lot_id = lot1
        self.assertEqual(move_line.product_qty, 5)  # don't change reservation when assgning a lot now

        move1._action_done()
        self.assertEqual(move_line.product_qty, 0)  # change reservation to 0 for done move
        self.assertEqual(move1.state, 'done')

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product3, self.stock_location)), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product3, self.stock_location, lot_id=lot1, strict=True)), 0.0)

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
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
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

        move1._action_done()
        self.assertEqual(untracked_move_line.product_qty, 0)  # change reservation to 0 for done move
        self.assertEqual(tracked_move_line.product_qty, 0)  # change reservation to 0 for done move
        self.assertEqual(move1.state, 'done')

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot2, strict=True), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product3, self.stock_location)), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product3, self.stock_location, lot_id=lot1, strict=True)), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product3, self.stock_location, lot_id=lot2, strict=True)), 0.0)

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, lot_id=lot2), 1.0)

        move1.move_line_ids.lot_id = lot2.id

        # reserved_availability should always been 0 for done move.
        self.assertEqual(move1.reserved_availability, 0.0)
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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf2_location, allow_negative=True), -1.0)

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        move2 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2._action_confirm()
        move2._action_assign()

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(move1.product_uom_qty, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        # edit once done, we actually moved 2 products
        move1.move_line_ids.qty_done = 2

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location, allow_negative=True), -1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, allow_negative=True), -1.0)
        self.assertEqual(move1.product_uom_qty, 2.0)

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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(move1.product_uom_qty, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)

        # edit once done, we actually moved 2 products
        move1.move_line_ids.qty_done = 0

        self.assertEqual(move1.product_uom_qty, 0.0)
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
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10
        move1._action_done()

        quant = self.gather_relevant(self.product1, self.stock_location)
        self.assertEqual(len(quant), 1.0)

        # edit once done, we actually moved 2 products
        move1.move_line_ids.qty_done = 0

        quant = self.gather_relevant(self.product1, self.stock_location)
        self.assertEqual(len(quant), 0.0)
        self.assertEqual(move1.product_uom_qty, 0.0)

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
        self.assertEqual(move1.product_uom_qty, 10.0)
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
        self.assertEqual(move1.product_uom_qty, 15.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 15.0)

    def test_edit_done_move_line_12(self):
        """ Test that editing a done stock move line linked a tracked product correctly and directly
        adapts the transfer. In this case, we edit the lot to another one, but the original move line
        is not in the default product's UOM.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product3.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product3.id,
        })
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_done_move_line_12'})
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1.move_line_ids.lot_id = lot1.id
        move1._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot1), 12.0)

        # Change the done quantity from 1 dozen to two dozen
        move1.move_line_ids.qty_done = 2
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot1), 24.0)

    def test_edit_done_move_line_13(self):
        """ Test that editing a done stock move line linked to a packed and tracked product correctly
        and directly adapts the transfer. In this case, we edit the lot to another available one
        that we put in the same pack.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product3.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product3.id,
        })
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_5'})

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1.move_line_ids.lot_id = lot1.id
        move1.move_line_ids.result_package_id = package1.id
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot1, package_id=package1), 1.0)

        move1.move_line_ids.write({'lot_id': lot2.id})

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot1, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product3, self.stock_location, lot_id=lot2, package_id=package1), 1.0)

    def test_immediate_validate_1(self):
        """ In a picking with a single available move, clicking on validate without filling any
        quantities should open a wizard asking to process all the reservation (so, the whole move).
        """
        partner = self.env['res.partner'].create({'name': 'Jean'})
        picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        self.env['stock.move'].create({
            'name': 'test_immediate_validate_1',
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
        self.assertEqual(res_dict.get('res_model'), 'stock.immediate.transfer')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 10.0)

    def test_immediate_validate_2(self):
        """ In a picking with a single partially available move, clicking on validate without
        filling any quantities should open a wizard asking to process all the reservation (so, only
        a part of the initial demand). Validating this wizard should open another one asking for
        the creation of a backorder. If the backorder is created, it should contain the quantities
        not processed.
        """
        partner = self.env['res.partner'].create({'name': 'Jean'})
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 5.0)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        self.env['stock.move'].create({
            'name': 'test_immediate_validate_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_id': picking.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.action_assign()
        # Only 5 products are reserved on the move of 10, click on `button_validate`.
        res_dict = picking.button_validate()
        self.assertEqual(res_dict.get('res_model'), 'stock.immediate.transfer')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        res_dict_for_back_order = wizard.process()
        self.assertEqual(res_dict_for_back_order.get('res_model'), 'stock.backorder.confirmation')
        backorder_wizard = self.env[(res_dict_for_back_order.get('res_model'))].browse(res_dict_for_back_order.get('res_id'))
        # Chose to create a backorder.
        backorder_wizard.process()

        # Only 5 products should be processed on the initial move.
        self.assertEqual(picking.move_lines.state, 'done')
        self.assertEqual(picking.move_lines.quantity_done, 5.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 0.0)

        # The backoder should contain a move for the other 5 produts.
        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
        self.assertEqual(len(backorder), 1.0)
        self.assertEqual(backorder.move_lines.product_uom_qty, 5.0)

    def test_immediate_validate_3(self):
        """ In a picking with two moves, one partially available and one unavailable, clicking
        on validate without filling any quantities should open a wizard asking to process all the
        reservation (so, only a part of one of the moves). Validating this wizard should open
        another one asking for the creation of a backorder. If the backorder is created, it should
        contain the quantities not processed.
        """
        product5 = self.env['product.product'].create({
            'name': 'Product 5',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1)

        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
        })
        product1_move = self.env['stock.move'].create({
            'name': 'product1_move',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'picking_id': picking.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100,
        })
        product5_move = self.env['stock.move'].create({
            'name': 'product3_move',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'picking_id': picking.id,
            'product_id': product5.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100,
        })
        picking.action_confirm()
        picking.action_assign()

        # product1_move should be partially available (1/100), product5_move should be totally
        # unavailable (0/100)
        self.assertEqual(product1_move.state, 'partially_available')
        self.assertEqual(product5_move.state, 'confirmed')

        action = picking.button_validate()
        self.assertEqual(action.get('res_model'), 'stock.immediate.transfer')
        wizard = self.env[(action.get('res_model'))].browse(action.get('res_id'))
        action = wizard.process()
        self.assertTrue(isinstance(action, dict), 'Should open backorder wizard')
        self.assertEqual(action.get('res_model'), 'stock.backorder.confirmation')
        wizard = self.env[(action.get('res_model'))].browse(action.get('res_id'))
        wizard.process()
        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
        self.assertEqual(len(backorder), 1.0)

        # The backorder should contain 99 product1 and 100 product5.
        for backorder_move in backorder.move_lines:
            if backorder_move.product_id.id == self.product1.id:
                self.assertEqual(backorder_move.product_qty, 99)
            elif backorder_move.product_id.id == product5.id:
                self.assertEqual(backorder_move.product_qty, 100)

    def test_immediate_validate_4(self):
        """ In a picking with a single available tracked by lot move, clicking on validate without
        filling any quantities should pop up the immediate transfer wizard.
        """
        partner = self.env['res.partner'].create({'name': 'Jean'})
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product3.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product3, self.stock_location, 5.0, lot_id=lot1)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        # move from shelf1
        self.env['stock.move'].create({
            'name': 'test_immediate_validate_4',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_id': picking.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        picking.action_confirm()
        picking.action_assign()
        # No quantites filled, immediate transfer wizard should pop up.
        immediate_trans_wiz_dict = picking.button_validate()
        self.assertEqual(immediate_trans_wiz_dict.get('res_model'), 'stock.immediate.transfer')
        immediate_trans_wiz = self.env[immediate_trans_wiz_dict['res_model']].browse(immediate_trans_wiz_dict['res_id'])
        immediate_trans_wiz.process()

        self.assertEqual(picking.move_lines.quantity_done, 5.0)
        # Check move_lines data
        self.assertEqual(len(picking.move_lines.move_line_ids), 1)
        self.assertEqual(picking.move_lines.move_line_ids.lot_id, lot1)
        self.assertEqual(picking.move_lines.move_line_ids.qty_done, 5.0)
        # Check quants data
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product1, self.stock_location)), 0.0)

    def _create_picking_test_immediate_validate_5(self, picking_type_id, product_id):
        picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': picking_type_id.id,
        })
        self.env['stock.move'].create({
            'name': 'move1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_id': picking.id,
            'picking_type_id': picking_type_id.id,
            'product_id': product_id.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })

        picking.action_confirm()

        for line in picking.move_line_ids:
            line.qty_done = line.product_uom_qty

        return picking

    def test_immediate_validate_5(self):
        """ In a receipt with a single tracked by serial numbers move, clicking on validate without
        filling any quantities nor lot should open an UserError except if the picking type is
        configured to allow otherwise.
        """
        picking_type_id = self.env.ref('stock.picking_type_in')
        product_id = self.product2
        self.assertTrue(picking_type_id.use_create_lots or picking_type_id.use_existing_lots)
        self.assertEqual(product_id.tracking, 'serial')

        picking = self._create_picking_test_immediate_validate_5(picking_type_id, product_id)
        # should raise because no serial numbers were specified
        self.assertRaises(UserError, picking.button_validate)

        picking_type_id.use_create_lots = False
        picking_type_id.use_existing_lots = False
        picking = self._create_picking_test_immediate_validate_5(picking_type_id, product_id)
        picking.button_validate()
        self.assertEqual(picking.state, 'done')

    def test_immediate_validate_6(self):
        """ In a receipt picking with two moves, one tracked and one untracked, clicking on
        validate without filling any quantities should displays an UserError as long as no quantity
        done and lot_name is set on the tracked move. Now if the user validates the picking, the
        wizard telling the user all reserved quantities will be processed will NOT be opened. This
        wizard is only opene if no quantities were filled. So validating the picking at this state
        will open another wizard asking for the creation of a backorder. Now, if the user processed
        on the second move more than the reservation, a wizard will ask him to confirm.
        """
        picking_type = self.env.ref('stock.picking_type_in')
        picking_type.use_create_lots = True
        picking_type.use_existing_lots = False
        picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': picking_type.id,
        })
        self.env['stock.move'].create({
            'name': 'product1_move',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_id': picking.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
        })
        product3_move = self.env['stock.move'].create({
            'name': 'product3_move',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_id': picking.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
        })
        picking.action_confirm()
        picking.action_assign()

        with self.assertRaises(UserError):
            picking.button_validate()
        product3_move.move_line_ids[0].qty_done = 1
        with self.assertRaises(UserError):
            picking.button_validate()
        product3_move.move_line_ids[0].lot_name = '271828'
        action = picking.button_validate()  # should open backorder wizard

        self.assertTrue(isinstance(action, dict), 'Should open backorder wizard')
        self.assertEqual(action.get('res_model'), 'stock.backorder.confirmation')

        product3_move.move_line_ids[0].qty_done = 2
        action = picking.button_validate()  # should request confirmation
        self.assertTrue(isinstance(action, dict), 'Should open overprocessing wizard')
        self.assertEqual(action.get('res_model'), 'stock.overprocessed.transfer')

    def test_immediate_validate_7(self):
        """ In a picking with a single unavailable move, clicking on validate without filling any
        quantities should display an UserError telling the user he cannot process a picking without
        any processed quantity.
        """
        partner = self.env['res.partner'].create({'name': 'Jean'})
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        self.env['stock.move'].create({
            'name': 'test_immediate_validate_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_id': picking.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.action_assign()
        # No products are reserved on the move of 10, click on `button_validate`.
        with self.assertRaises(UserError):
            picking.button_validate()

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
        (move1 + move2)._action_confirm()
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
        storable product.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1)
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product1.id,
            'product_uom_id':self.product1.uom_id.id,
            'scrap_qty': 1,
        })
        scrap.do_scrap()
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
        scrap.do_scrap()
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
            'name': 'test_scrap_3',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        scrap = self.env['stock.scrap'].create({
            'product_id': self.product1.id,
            'product_uom_id':self.product1.uom_id.id,
            'scrap_qty': 1,
        })
        scrap.do_scrap()
        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(len(move1.move_line_ids), 0)

    def test_scrap_4(self):
        """ Scrap the product of a picking. Then modify the
        done linked stock move and ensure the scrap quantity is also
        updated.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 10)
        partner = self.env['res.partner'].create({'name': 'Kimberley'})
        picking = self.env['stock.picking'].create({
            'name': 'A single picking with one move to scrap',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'A move to confirm and scrap its product',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_id': picking.id,
        })
        move1._action_confirm()

        self.assertEqual(move1.state, 'confirmed')
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product1.id,
            'product_uom_id': self.product1.uom_id.id,
            'scrap_qty': 5,
            'picking_id': picking.id,
        })

        scrap.action_validate()
        self.assertEqual(len(picking.move_lines), 2)
        scrapped_move = picking.move_lines.filtered(lambda m: m.state == 'done')
        self.assertTrue(scrapped_move, 'No scrapped move created.')
        self.assertEqual(scrapped_move.scrap_ids.ids, [scrap.id], 'Wrong scrap linked to the move.')
        self.assertEqual(scrap.scrap_qty, 5, 'Scrap quantity has been modified and is not correct anymore.')

        scrapped_move.quantity_done = 8
        self.assertEqual(scrap.scrap_qty, 8, 'Scrap quantity is not updated.')

    def test_scrap_5(self):
        """ Scrap the product of a reserved move line where the product is reserved in another
        unit of measure. Check that the move line is correctly updated after the scrap.
        """
        # 4 units are available in stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4)

        # try to reserve a dozen
        partner = self.env['res.partner'].create({'name': 'Kimberley'})
        picking = self.env['stock.picking'].create({
            'name': 'A single picking with one move to scrap',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'A move to confirm and scrap its product',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1.0,
            'picking_id': picking.id,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.reserved_availability, 0.33)

        # scrap a unit
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product1.id,
            'product_uom_id': self.product1.uom_id.id,
            'scrap_qty': 1,
            'picking_id': picking.id,
        })
        scrap.action_validate()

        self.assertEqual(scrap.state, 'done')
        self.assertEqual(move1.reserved_availability, 0.25)

    def test_scrap_6(self):
        """ Check that scrap correctly handle UoM. """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1)
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product1.id,
            'product_uom_id': self.uom_dozen.id,
            'scrap_qty': 1,
        })
        warning_message = scrap.action_validate()
        self.assertEqual(warning_message.get('res_model', 'Wrong Model'), 'stock.warn.insufficient.qty.scrap')
        insufficient_qty_wizard = self.env['stock.warn.insufficient.qty.scrap'].create({
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
            'scrap_id': scrap.id
        })
        insufficient_qty_wizard.action_done()
        self.assertEqual(self.env['stock.quant']._gather(self.product1, self.stock_location).quantity, -11)

    def test_in_date_1(self):
        """ Check that moving a tracked quant keeps the incoming date.
        """
        move1 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.lot_name = 'lot1'
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        quant = self.gather_relevant(self.product3, self.stock_location)
        self.assertEqual(len(quant), 1.0)
        self.assertNotEqual(quant.in_date, False)

        # Keep a reference to the initial incoming date in order to compare it later.
        initial_incoming_date = quant.in_date

        move2 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 1
        move2._action_done()

        quant = self.gather_relevant(self.product3, self.pack_location)
        self.assertEqual(len(quant), 1.0)
        self.assertEqual(quant.in_date, initial_incoming_date)

    def test_in_date_2(self):
        """ Check that editing a done move line for a tracked product and changing its lot
        correctly restores the original lot with its incoming date and remove the new lot
        with its incoming date.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product3.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product3.id,
        })
        # receive lot1
        move1 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.lot_id = lot1
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        # receive lot2
        move2 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.lot_id = lot2
        move2.move_line_ids.qty_done = 1
        move2._action_done()

        initial_in_date_lot2 = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product3.id),
            ('lot_id', '=', lot2.id),
        ]).in_date

        # Edit lot1's incoming date.
        quant_lot1 = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product3.id),
            ('lot_id', '=', lot1.id),
        ])
        from odoo.fields import Datetime
        from datetime import timedelta
        initial_in_date_lot1 = Datetime.now() - timedelta(days=5)
        quant_lot1.in_date = initial_in_date_lot1

        # Move one quant to pack location
        move3 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 1
        move3._action_done()
        quant_in_pack = self.env['stock.quant'].search([
            ('product_id', '=', self.product3.id),
            ('location_id', '=', self.pack_location.id),
        ])
        # As lot1 has an older date and FIFO is set by default, it's the one that should be
        # in pack.
        self.assertEqual(len(quant_in_pack), 1)
        self.assertAlmostEqual(quant_in_pack.in_date, initial_in_date_lot1, delta=timedelta(seconds=1))
        self.assertEqual(quant_in_pack.lot_id, lot1)

        # Now, edit the move line and actually move the other lot
        move3.move_line_ids.lot_id = lot2

        # Check that lot1 correctly is back to stock with its right in_date
        quant_lot1 = self.env['stock.quant'].search([
            ('location_id.usage', '=', 'internal'),
            ('product_id', '=', self.product3.id),
            ('lot_id', '=', lot1.id),
            ('quantity', '!=', 0),
        ])
        self.assertEqual(quant_lot1.location_id, self.stock_location)
        self.assertAlmostEqual(quant_lot1.in_date, initial_in_date_lot1, delta=timedelta(seconds=1))

        # Check that lo2 is in pack with is right in_date
        quant_lot2 = self.env['stock.quant'].search([
            ('location_id.usage', '=', 'internal'),
            ('product_id', '=', self.product3.id),
            ('lot_id', '=', lot2.id),
            ('quantity', '!=', 0),
        ])
        self.assertEqual(quant_lot2.location_id, self.pack_location)
        self.assertAlmostEqual(quant_lot2.in_date, initial_in_date_lot2, delta=timedelta(seconds=1))

    def test_in_date_3(self):
        """ Check that, when creating a move line on a done stock move, the lot and its incoming
        date are correctly moved to the destination location.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product3.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product3.id,
        })
        # receive lot1
        move1 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.lot_id = lot1
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        # receive lot2
        move2 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.lot_id = lot2
        move2.move_line_ids.qty_done = 1
        move2._action_done()

        initial_in_date_lot2 = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product3.id),
            ('lot_id', '=', lot2.id),
            ('quantity', '!=', 0),
        ]).in_date

        # Edit lot1's incoming date.
        quant_lot1 = self.env['stock.quant'].search([
            ('location_id.usage', '=', 'internal'),
            ('product_id', '=', self.product3.id),
            ('lot_id', '=', lot1.id),
            ('quantity', '!=', 0),
        ])
        from odoo.fields import Datetime
        from datetime import timedelta
        initial_in_date_lot1 = Datetime.now() - timedelta(days=5)
        quant_lot1.in_date = initial_in_date_lot1

        # Move one quant to pack location
        move3 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product3.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 1
        move3._action_done()

        # Now, also move lot2
        self.env['stock.move.line'].create({
            'move_id': move3.id,
            'product_id': move3.product_id.id,
            'qty_done': 1,
            'product_uom_id': move3.product_uom.id,
            'location_id': move3.location_id.id,
            'location_dest_id': move3.location_dest_id.id,
            'lot_id': lot2.id,
        })

        quants = self.env['stock.quant'].search([
            ('location_id.usage', '=', 'internal'),
            ('product_id', '=', self.product3.id),
            ('quantity', '!=', 0),
        ])
        self.assertEqual(len(quants), 2)
        for quant in quants:
            if quant.lot_id == lot1:
                self.assertAlmostEqual(quant.in_date, initial_in_date_lot1, delta=timedelta(seconds=1))
            elif quant.lot_id == lot2:
                self.assertAlmostEqual(quant.in_date, initial_in_date_lot2, delta=timedelta(seconds=1))

    def test_transit_1(self):
        """ Receive some products, send some to transit, check the product's `available_qty`
        computed field with or without the "company_owned" key in the context.
        """
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10
        move1._action_done()

        self.assertEqual(self.product1.qty_available, 10.0)

        move2 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.transit_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 5
        move2._action_done()

        self.assertEqual(self.product1.qty_available, 5.0)
        self.assertEqual(self.product1.with_context(company_owned=True).qty_available, 10.0)

    def test_edit_initial_demand_1(self):
        """ Increase initial demand once everything is reserved and check if
        the existing move_line is updated.
        """
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.product_uom_qty = 15
        # _action_assign is automatically called
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move1.product_uom_qty, 15)
        self.assertEqual(len(move1.move_line_ids), 1)

    def test_edit_initial_demand_2(self):
        """ Decrease initial demand once everything is reserved and check if
        the existing move_line has been dropped after the updated and another
        is created once the move is reserved.
        """
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        move1.product_uom_qty = 5
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move1.product_uom_qty, 5)
        self.assertEqual(len(move1.move_line_ids), 1)

    def test_initial_demand_3(self):
        """ Increase the initial demand on a receipt picking, the system should automatically
        reserve the new quantity.
        """
        picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'immediate_transfer': True,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'picking_id': picking.id,
        })
        picking._autoconfirm_picking()
        self.assertEqual(picking.state, 'assigned')
        move1.product_uom_qty = 12
        self.assertEqual(picking.state, 'assigned')

    def test_initial_demand_4(self):
        """ Increase the initial demand on a delivery picking, the system should not automatically
        reserve the new quantity.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 12)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'picking_id': picking.id,
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(picking.state, 'assigned')
        move1.product_uom_qty = 12
        self.assertEqual(picking.state, 'assigned')  # actually, partially available
        self.assertEqual(move1.state, 'partially_available')
        picking.action_assign()
        self.assertEqual(move1.state, 'assigned')

    def test_change_product_type(self):
        """ Changing type of an existing product will raise a user error if some move
        are reserved.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 10)
        move1 = self.env['stock.move'].create({
            'name': 'test_customer',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1._action_confirm()
        move1._action_assign()

        with self.assertRaises(UserError):
            self.product1.type = 'consu'
        move1._action_cancel()
        self.product1.type = 'consu'

        move2 = self.env['stock.move'].create({
            'name': 'test_customer',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })

        move2._action_confirm()
        move2._action_assign()

        with self.assertRaises(UserError):
            self.product1.type = 'product'
        move2._action_cancel()
        self.product1.type = 'product'

    def test_edit_done_picking_1(self):
        """ Add a new move line in a done picking should generate an
        associated move.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 12)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'picking_id': picking.id,
        })
        picking.action_confirm()
        picking.action_assign()
        move1.quantity_done = 10
        picking.action_done()

        self.assertEqual(len(picking.move_lines), 1, 'One move should exist for the picking.')
        self.assertEqual(len(picking.move_line_ids), 1, 'One move line should exist for the picking.')

        ml = self.env['stock.move.line'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'qty_done': 2.0,
            'picking_id': picking.id,
        })

        self.assertEqual(len(picking.move_lines), 2, 'The new move associated to the move line does not exist.')
        self.assertEqual(len(picking.move_line_ids), 2, 'It should be 2 move lines for the picking.')
        self.assertTrue(ml.move_id in picking.move_lines, 'Links are not correct between picking, moves and move lines.')
        self.assertEqual(picking.state, 'done', 'Picking should still done after adding a new move line.')
        self.assertTrue(all(move.state == 'done' for move in picking.move_lines), 'Wrong state for move.')

    def test_put_in_pack_1(self):
        """ Check that reserving a move and adding its move lines to
        different packages work as expected.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'picking_id': picking.id,
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0)
        move1.quantity_done = 1
        picking.put_in_pack()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0)
        self.assertEqual(len(picking.move_line_ids), 2)
        unpacked_ml = picking.move_line_ids.filtered(lambda ml: not ml.result_package_id)
        self.assertEqual(unpacked_ml.product_qty, 1)
        unpacked_ml.qty_done = 1
        picking.put_in_pack()
        self.assertEqual(len(picking.move_line_ids), 2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0)
        picking.button_validate()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.customer_location), 2)
