# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class StockMove(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(StockMove, cls).setUpClass()
        group_stock_multi_locations = cls.env.ref('stock.group_stock_multi_locations')
        cls.env.user.write({'groups_id': [(4, group_stock_multi_locations.id, 0)]})
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.pack_location = cls.env.ref('stock.location_pack_zone')
        cls.pack_location.active = True
        cls.transit_location = cls.env['stock.location'].search([
            ('company_id', '=', cls.env.company.id),
            ('usage', '=', 'transit'),
            ('active', '=', False)
        ], limit=1)
        cls.transit_location.active = True
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        cls.product = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product_serial = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product_lot = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'lot',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product_consu = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
            'categ_id': cls.env.ref('product.product_category_all').id,
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1._action_confirm()
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
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.supplier_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.supplier_location, allow_negative=True), -100.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 100.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.supplier_location)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)

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
            'product_id': self.product_lot.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1._action_confirm()
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

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.supplier_location), 0.0)
        supplier_quants = self.gather_relevant(self.product_lot, self.supplier_location)
        self.assertEqual(sum(supplier_quants.mapped('quantity')), -5.0)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location), 5.0)
        self.assertEqual(len(self.gather_relevant(self.product_lot, self.supplier_location)), 1.0)
        quants = self.gather_relevant(self.product_lot, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        for quant in quants:
            self.assertNotEqual(quant.in_date, False)

    def test_in_3(self):
        """ Receive 5 serial-tracked products from a supplier. The system should create 5 different
        move line.
        """
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1._action_confirm()
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
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.supplier_location), 0.0)
        supplier_quants = self.gather_relevant(self.product_serial, self.supplier_location)
        self.assertEqual(sum(supplier_quants.mapped('quantity')), -5.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 5.0)

        self.assertEqual(len(self.gather_relevant(self.product_serial, self.supplier_location)), 5.0)
        quants = self.gather_relevant(self.product_serial, self.stock_location)
        self.assertEqual(len(quants), 5.0)
        for quant in quants:
            self.assertNotEqual(quant.in_date, False)

    def test_out_1(self):
        """ Send products to a client. Check that a move line is created reserving products in
        stock and that the delivery correctly remove the single quant in stock.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 100)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 100.0)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        # Should be a reserved quantity and thus a quant.
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)

        # fill the move line
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 100.0)
        self.assertEqual(move_line.qty_done, 0.0)
        move_line.qty_done = 100.0

        # validation
        move1._action_done()
        self.assertEqual(move1.state, 'done')
        # Check there is one quant in customer location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.customer_location), 100.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.customer_location)), 1.0)
        # there should be no quant amymore in the stock location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 0.0)

    def test_out_2(self):
        """ Send a consumable product to a client. Check that a move line is created but
            quants are not impacted.
        """
        # make some stock

        self.product.type = 'consu'
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        self.assertEqual(move1.state, 'draft')

        # confirmation
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        # Should be a reserved quantity and thus a quant.
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 0.0)

        # fill the move line
        move_line = move1.move_line_ids[0]
        self.assertEqual(move_line.product_qty, 100.0)
        self.assertEqual(move_line.qty_done, 0.0)
        move_line.qty_done = 100.0

        # validation
        move1._action_done()
        self.assertEqual(move1.state, 'done')
        # no quants are created in the customer location since it's a consumable
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.customer_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.customer_location)), 0.0)
        # there should be no quant amymore in the stock location
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 0.0)

    def test_mixed_tracking_reservation_1(self):
        """ Send products tracked by lot to a customer. In your stock, there are tracked and
        untracked quants. Two moves lines should be created: one for the tracked ones, another
        for the untracked ones.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_lot, self.stock_location, 2)
        self.env['stock.quant']._update_available_quantity(self.product_lot, self.stock_location, 3, lot_id=lot1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location), 5.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_lot.id,
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
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 2)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1, lot_id=lot2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 4.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
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
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot4 = self.env['stock.production.lot'].create({
            'name': 'lot4',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        untracked_move_line = move1.move_line_ids.filtered(lambda ml: not ml.lot_id)
        untracked_move_line[0].lot_id = lot3
        untracked_move_line[1].lot_id = lot4
        for ml in move1.move_line_ids:
            self.assertEqual(ml.product_qty, 1.0)

        # no changes on quants, even if i made some move lines with a lot id whom reserved on untracked quants
        self.assertEqual(len(self.gather_relevant(self.product_serial, self.stock_location, strict=True)), 1.0)  # with a qty of 2
        self.assertEqual(len(self.gather_relevant(self.product_serial, self.stock_location, lot_id=lot1, strict=True).filtered(lambda q: q.lot_id)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product_serial, self.stock_location, lot_id=lot2, strict=True).filtered(lambda q: q.lot_id)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product_serial, self.stock_location, lot_id=lot3, strict=True).filtered(lambda q: q.lot_id)), 0)
        self.assertEqual(len(self.gather_relevant(self.product_serial, self.stock_location, lot_id=lot4, strict=True).filtered(lambda q: q.lot_id)), 0)

        move1.move_line_ids.write({'qty_done': 1.0})

        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot2, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot3, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot4, strict=True), 0.0)

    def test_mixed_tracking_reservation_3(self):
        """ Send two products tracked by lot to a customer. In your stock, there two tracked quants
        and two untracked. Once the move is validated, add move lines to also move the two untracked
        ones and assign them serial numbers on the fly. The final quantity in stock should be 0, not
        negative.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1, lot_id=lot2)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 2.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.write({'qty_done': 1.0})
        move1._action_done()

        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 2)
        lot3 = self.env['stock.production.lot'].create({
            'name': 'lot3',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot4 = self.env['stock.production.lot'].create({
            'name': 'lot4',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
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

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot2, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot3, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot4, strict=True), 0.0)

    def test_mixed_tracking_reservation_4(self):
        """ Send two products tracked by lot to a customer. In your stock, there two tracked quants
        and on untracked. Once the move is validated, edit one of the done move line to change the
        serial number to one that is not in stock. The original serial should go back to stock and
        the untracked quant should be tracked on the fly and sent instead.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1, lot_id=lot2)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 2.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.write({'qty_done': 1.0})
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot2, strict=True), 0.0)

        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1)
        lot3 = self.env['stock.production.lot'].create({
            'name': 'lot3',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })

        move1.move_line_ids[1].lot_id = lot3

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot2, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot3, strict=True), 0.0)

    def test_mixed_tracking_reservation_5(self):
        move1 = self.env['stock.move'].create({
            'name': 'test_jenaimarre_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'confirmed')

        # create an untracked quant
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0)
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
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
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product_serial, self.stock_location)), 0.0)

    def test_mixed_tracking_reservation_6(self):
        # create an untracked quant
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0)
        move1 = self.env['stock.move'].create({
            'name': 'test_jenaimarre_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')

        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })

        move_line = move1.move_line_ids
        move_line.lot_id = lot1
        self.assertEqual(move_line.product_qty, 1.0)
        move_line.lot_id = lot2
        self.assertEqual(move_line.product_qty, 1.0)
        move_line.qty_done = 1

        # validating the move line should move the lot, not create a negative quant in stock
        move1._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product_serial, self.stock_location)), 0.0)

    def test_mixed_tracking_reservation_7(self):
        """ Similar test_mixed_tracking_reservation_2 but creates first the tracked quant, then the
        untracked ones. When adding a lot to the untracked move line, it should not decrease the
        untracked quant then increase a non-existing tracked one that will fallback on the
        untracked quant.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 2.0)
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
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

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot2, strict=True), 0.0)
        quants = self.gather_relevant(self.product_serial, self.stock_location)
        self.assertEqual(len(quants), 0)

    def test_mixed_tracking_reservation_8(self):
        """ Send one product tracked by lot to a customer. In your stock, there are one tracked and
        one untracked quant. Reserve the move, then edit the lot to one not present in stock. The
        system will update the reservation and use the untracked quant. Now unreserve, no error
        should happen
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })

        # at first, we only make the tracked quant available in stock to make sure this one is selected
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1, lot_id=lot1)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_mixed_tracking_reservation_7',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(move1.move_line_ids.lot_id.id, lot1.id)

        # change the lot_id to one not available in stock while an untracked quant is available
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1)
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        move1.move_line_ids.lot_id = lot2
        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(move1.move_line_ids.lot_id.id, lot2.id)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1, strict=True), 1.0)

        # unreserve
        move1._do_unreserve()

        self.assertEqual(move1.reserved_availability, 0.0)
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.stock_location, lot_id=lot1, strict=True), 2.0)

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
        # putaway from stock to shelf1
        putaway = self.env['stock.putaway.rule'].create({
            'category_id': self.env.ref('product.product_category_all').id,
            'location_in_id': self.stock_location.id,
            'location_out_id': shelf1_location.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)]
        })

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
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
        # putaway from stock to shelf1
        putaway = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': shelf1_location.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
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
        putaway_category = self.env['stock.putaway.rule'].create({
            'category_id': self.env.ref('product.product_category_all').id,
            'location_in_id': self.supplier_location.id,
            'location_out_id': shelf1_location.id,
        })
        putaway_product = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.supplier_location.id,
            'location_out_id': shelf2_location.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(6, 0, [
                putaway_category.id,
                putaway_product.id
            ])],
        })

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_3',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
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
        # putaway from stock to shelf1
        putaway_category = self.env['stock.putaway.rule'].create({
            'category_id': self.env.ref('product.product_category_all').id,
            'location_in_id': self.stock_location.id,
            'location_out_id': shelf1_location.id,
        })
        putaway_product = self.env['stock.putaway.rule'].create({
            'product_id': self.product_consu.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': shelf2_location.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(6, 0, [
                putaway_category.id,
                putaway_product.id,
            ])],
        })

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_4',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf1_location.id)

    def test_putaway_5(self):
        """ Receive products from a supplier. Check that putaway rules are rightly applied on
        the receipt move line.
        """
        # This test will apply putaway strategy by category.
        # We check here that the putaway by category works when the category is
        # set on parent category of the product.

        shelf_location = self.env['stock.location'].create({
            'name': 'shelf',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        putaway = self.env['stock.putaway.rule'].create({
            'category_id': self.env.ref('product.product_category_all').id,
            'location_in_id': self.supplier_location.id,
            'location_out_id': shelf_location.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(6, 0, [
                putaway.id,
            ])],
        })
        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_5',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf_location.id)

    def test_putaway_6(self):
        """ Receive products from a supplier. Check that putaway rules are rightly applied on
        the receipt move line.
        """
        # This test will apply two putaway strategies by category. We check here
        # that the most specific putaway takes precedence.

        child_category = self.env['product.category'].create({
            'name': 'child_category',
            'parent_id': self.ref('product.product_category_all'),
        })
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
        putaway_category_all = self.env['stock.putaway.rule'].create({
            'category_id': self.env.ref('product.product_category_all').id,
            'location_in_id': self.supplier_location.id,
            'location_out_id': shelf1_location.id,
        })
        putaway_category_office_furn = self.env['stock.putaway.rule'].create({
            'category_id': child_category.id,
            'location_in_id': self.supplier_location.id,
            'location_out_id': shelf2_location.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(6, 0, [
                putaway_category_all.id,
                putaway_category_office_furn.id,
            ])],
        })
        self.product.categ_id = child_category

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_6',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf2_location.id)

    def test_putaway_with_storage_category_1(self):
        """Receive a product. Test the product will be move to a child location
        with correct storage category.
        """
        # storage category
        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category"
        })

        self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })

        # putaway from stock to child location with storage_category
        putaway = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        move1 = self.env['stock.move'].create({
            'name': 'test_move_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf2_location.id)

    def test_putaway_with_storage_category_2(self):
        """Receive a product twice. Test first time the putaway applied since we
        have enough space, and second time it is not since the location is full.
        """
        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category"
        })
        # set the capacity for the product in this storage category to be 100
        storage_category_form = Form(storage_category, view='stock.stock_storage_category_form')
        with storage_category_form.product_capacity_ids.new() as line:
            line.product_id = self.product
            line.quantity = 100
        storage_category = storage_category_form.save()

        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })
        # putaway from stock to child location with storage_category
        putaway = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        # first move
        move1 = self.env['stock.move'].create({
            'name': 'test_move_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf1_location.id)

        # second move
        move2 = self.env['stock.move'].create({
            'name': 'test_move_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move2._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move2.move_line_ids), 1)

        # check if the putaway wasn't applied
        self.assertEqual(move2.move_line_ids.location_dest_id.id, self.stock_location.id)

    def test_putaway_with_storage_category_3(self):
        """Received products twice, set storage category to only accept new
        product when empty. Check the first time putaway rule applied and second
        time not.
        """
        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category",
            'allow_new_product': "empty",
        })

        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })
        # putaway from stock to child location with storage_category
        putaway = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        # first move
        move1 = self.env['stock.move'].create({
            'name': 'test_move_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        move_line.qty_done = 100
        move1._action_done()
        self.assertEqual(move1.state, 'done')

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf1_location.id)

        # second move
        move2 = self.env['stock.move'].create({
            'name': 'test_move_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move2._action_confirm()
        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(len(move2.move_line_ids), 1)

        # check if the putaway wasn't applied
        self.assertEqual(move2.move_line_ids.location_dest_id.id, self.stock_location.id)

    def test_putaway_with_storage_category_4(self):
        """Received products, set storage category to only accept same product.
        Check the putaway rule can't be applied when the location has different
        products.
        """
        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category",
            'allow_new_product': "same",
        })

        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })
        # putaway from stock to child location with storage_category
        putaway = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        # create a different product and its quant
        product2 = self.env['product.product'].create({
            'name': 'Product 2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.env['stock.quant'].create({
            'product_id': product2.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': shelf1_location.id,
            'quantity': 1,
            'reserved_quantity': 0,
        })

        move1 = self.env['stock.move'].create({
            'name': 'test_move_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        move_line = move1.move_line_ids[0]
        move_line.qty_done = 100
        move1._action_done()
        self.assertEqual(move1.state, 'done')

        # check if the putaway can't be applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, self.stock_location.id)

    def test_putaway_with_storage_category_5(self):
        """Receive a package. Test the package will be move to a child location
        with correct storage category.
        """
        # storage category
        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category"
        })

        package_type = self.env['stock.package.type'].create({
            'name': "package type",
        })

        self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })

        # putaway from stock to child location with storage_category
        putaway = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
            'package_type_ids': [(4, package_type.id, 0)],
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        package = self.env['stock.quant.package'].create({
            'name': 'package',
            'package_type_id': package_type.id,
        })

        move1 = self.env['stock.move'].create({
            'name': 'test_move_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        move_form = Form(move1, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.result_package_id = package
            line.qty_done = 100
        move1 = move_form.save()
        move1._action_done()

        # check if the putaway was rightly applied
        self.assertEqual(package.location_id.id, shelf2_location.id)

    def test_putaway_with_storage_category_6(self):
        """Receive package with same package type twice. Check putaway rule can
        be applied on the first one but not the second one due to no space.
        """
        # storage category
        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category"
        })

        package_type = self.env['stock.package.type'].create({
            'name': "package type",
        })

        # set the capacity for the package type in this storage category to be 1
        storage_category_form = Form(storage_category, view='stock.stock_storage_category_form')
        with storage_category_form.package_capacity_ids.new() as line:
            line.package_type_id = package_type
            line.quantity = 1
        storage_category = storage_category_form.save()

        self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })

        # putaway from stock to child location with storage_category
        putaway = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
            'package_type_ids': [(4, package_type.id, 0)],
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        # first package
        package1 = self.env['stock.quant.package'].create({
            'name': 'package 1',
            'package_type_id': package_type.id,
        })

        move1 = self.env['stock.move'].create({
            'name': 'test_move_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        move_form = Form(move1, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.result_package_id = package1
            line.qty_done = 100
        move1 = move_form.save()
        move1._action_done()

        # check if the putaway was rightly applied
        self.assertEqual(package1.location_id.id, shelf2_location.id)

        # second package
        package2 = self.env['stock.quant.package'].create({
            'name': 'package 2',
            'package_type_id': package_type.id,
        })

        move2 = self.env['stock.move'].create({
            'name': 'test_move_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move2._action_confirm()
        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(len(move2.move_line_ids), 1)

        move_form = Form(move2, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.result_package_id = package2
            line.qty_done = 100
        move2 = move_form.save()
        move2._action_done()

        # check if the putaway wasn't applied
        self.assertEqual(package2.location_id.id, self.stock_location.id)

    def test_putaway_with_storage_category_7(self):
        """Receive package with same package type twice, set storage category to
        only accept new product when empty. Check putaway rule can be applied on
        the first one but not the second one.
        """
        # storage category
        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category",
            'allow_new_product': "empty",
        })

        package_type = self.env['stock.package.type'].create({
            'name': "package type",
        })

        # set the capacity for the package type in this storage category to be 100
        storage_category_form = Form(storage_category, view='stock.stock_storage_category_form')
        with storage_category_form.package_capacity_ids.new() as line:
            line.package_type_id = package_type
            line.quantity = 100
        storage_category = storage_category_form.save()

        self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })

        # putaway from stock to child location with storage_category
        putaway = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
            'package_type_ids': [(4, package_type.id, 0)],
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        # first package
        package1 = self.env['stock.quant.package'].create({
            'name': 'package 1',
            'package_type_id': package_type.id,
        })

        move1 = self.env['stock.move'].create({
            'name': 'test_move_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        move_form = Form(move1, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.result_package_id = package1
            line.qty_done = 100
        move1 = move_form.save()
        move1._action_done()

        # check if the putaway was rightly applied
        self.assertEqual(package1.location_id.id, shelf2_location.id)

        # second package
        package2 = self.env['stock.quant.package'].create({
            'name': 'package 2',
            'package_type_id': package_type.id,
        })

        move2 = self.env['stock.move'].create({
            'name': 'test_move_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move2._action_confirm()
        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(len(move2.move_line_ids), 1)

        move_form = Form(move2, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.result_package_id = package2
            line.qty_done = 100
        move2 = move_form.save()
        move2._action_done()

        # check if the putaway wasn't applied
        self.assertEqual(package2.location_id.id, self.stock_location.id)

    def test_putaway_with_storage_category_8(self):
        """Receive package withs different products, set storage category to only
        accept same product. Check putaway rule can be applied on the first one
        but not the second one.
        """
        # storage category
        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category",
            'allow_new_product': "same",
        })

        package_type = self.env['stock.package.type'].create({
            'name': "package type",
        })

        # set the capacity for the package type in this storage category to be 100
        storage_category_form = Form(storage_category, view='stock.stock_storage_category_form')
        with storage_category_form.package_capacity_ids.new() as line:
            line.package_type_id = package_type
            line.quantity = 100
        storage_category = storage_category_form.save()

        self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })

        # putaway from stock to child location for package type
        putaway = self.env['stock.putaway.rule'].create({
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
            'package_type_ids': [(4, package_type.id, 0)],
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        # first package
        package1 = self.env['stock.quant.package'].create({
            'name': 'package 1',
            'package_type_id': package_type.id,
        })

        move1 = self.env['stock.move'].create({
            'name': 'test_move_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        move_form = Form(move1, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.result_package_id = package1
            line.qty_done = 100
        move1 = move_form.save()
        move1._action_done()

        # check if the putaway was rightly applied
        self.assertEqual(package1.location_id.id, shelf2_location.id)

        # second package
        package2 = self.env['stock.quant.package'].create({
            'name': 'package 2',
            'package_type_id': package_type.id,
        })

        product2 = self.env['product.product'].create({
            'name': 'Product 2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        move2 = self.env['stock.move'].create({
            'name': 'test_move_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move2._action_confirm()
        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(len(move2.move_line_ids), 1)

        move_form = Form(move2, view='stock.view_stock_move_nosuggest_operations')
        with move_form.move_line_nosuggest_ids.new() as line:
            line.result_package_id = package2
            line.qty_done = 100
        move2 = move_form.save()
        move2._action_done()

        # check if the putaway wasn't applied
        self.assertEqual(package2.location_id.id, self.stock_location.id)

    def test_putaway_with_storage_category_9(self):
        """Receive a product twice. Test first time the putaway applied, and second
        time it is not since the products violate the max_weight limitaion.
        """
        self.product.weight = 1
        storage_category = self.env['stock.storage.category'].create({
            'name': "storage category",
            'max_weight': 100,
        })

        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })
        # putaway from stock to child location with storage_category
        putaway = self.env['stock.putaway.rule'].create({
            'product_id': self.product.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': storage_category.id,
        })
        self.stock_location.write({
            'putaway_rule_ids': [(4, putaway.id, 0)],
        })

        # first move
        move1 = self.env['stock.move'].create({
            'name': 'test_move_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move1._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        # check if the putaway was rightly applied
        self.assertEqual(move1.move_line_ids.location_dest_id.id, shelf1_location.id)

        # second move
        move2 = self.env['stock.move'].create({
            'name': 'test_move_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })
        move2._action_confirm()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move2.move_line_ids), 1)

        # check if the putaway wasn't applied since there are already 100kg products in the location
        self.assertEqual(move2.move_line_ids.location_dest_id.id, self.stock_location.id)

    def test_availability_1(self):
        """ Check that the `availability` field on a move is correctly computed when there is
        more than enough products in stock.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 150.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 150.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)
        self.assertEqual(move1.availability, 100.0)

    def test_availability_2(self):
        """ Check that the `availability` field on a move is correctly computed when there is
        not enough products in stock.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 50.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 50.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)
        self.assertEqual(move1.availability, 50.0)

    def test_availability_3(self):
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, -1.0, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot2)
        move1 = self.env['stock.move'].create({
            'name': 'test_availability_3',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move1.reserved_availability, 1.0)

    def test_availability_4(self):
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 30.0)
        move1 = self.env['stock.move'].create({
            'name': 'test_availability_4',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
            'product_id': self.product.id,
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

        stock_quants = self.gather_relevant(self.product, self.stock_location)
        self.assertEqual(len(stock_quants), 0)
        customer_quants = self.gather_relevant(self.product, self.customer_location)
        self.assertEqual(customer_quants.quantity, 30)
        self.assertEqual(customer_quants.reserved_quantity, 0)

    def test_availability_5(self):
        """ Check that rerun action assign only create new stock move
        lines instead of adding quantity in existing one.
        """
        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 2.0)
        # move from shelf1
        move = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4.0,
        })
        move._action_confirm()
        move._action_assign()

        self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 4.0)
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
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 6.0)

        # the move should not be reserved
        move = self.env['stock.move'].create({
            'name': 'test_availability_6',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1,
        })
        move._action_confirm()
        move._action_assign()
        self.assertEqual(move.state, 'confirmed')

        # the quants should be left untouched
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 6.0)

        # make 8 units available, the move should again not be reservabale
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2.0)
        move._action_assign()
        self.assertEqual(move.state, 'confirmed')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 8.0)

        # make 12 units available, this time the move should be reservable
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 4.0)
        move._action_assign()
        self.assertEqual(move.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

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
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.customer_location), 12.0)

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
                'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
            })
            self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot_id)

        # the move should be reserved
        move = self.env['stock.move'].create({
            'name': 'test_availability_7',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_serial.id,
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
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.customer_location), 12.0)
        self.assertEqual(len(self.gather_relevant(self.product_serial, self.customer_location)), 12)

    def test_availability_8(self):
        """ Test the assignment mechanism when the product quantity is decreased on a partially
            reserved stock move.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 3.0)
        self.assertAlmostEqual(self.product.qty_available, 3.0)

        move_partial = self.env['stock.move'].create({
            'name': 'test_partial',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })

        move_partial._action_confirm()
        move_partial._action_assign()
        self.assertAlmostEqual(self.product.virtual_available, -2.0)
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
            'product_id': self.product.id,
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
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 150.0)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 150.0)
        self.assertEqual(move1.availability, 100.0)

        # confirmation
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 50.0)

        # unreserve
        move1._do_unreserve()
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 150.0)
        self.assertEqual(move1.state, 'confirmed')

    def test_unreserve_2(self):
        """ Check that unreserving a stock move sets the products reserved as available and
        set the state back to confirmed even if they are in a pack.
        """
        package1 = self.env['stock.quant.package'].create({'name': 'test_unreserve_2_pack'})

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 150.0, package_id=package1)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_putaway_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package1), 150.0)
        self.assertEqual(move1.availability, 100.0)

        # confirmation
        move1._action_confirm()
        self.assertEqual(move1.state, 'confirmed')

        # assignment
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package1), 50.0)

        # unreserve
        move1._do_unreserve()
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package1), 150.0)
        self.assertEqual(move1.state, 'confirmed')

    def test_unreserve_3(self):
        """ Similar to `test_unreserve_1` but checking the quants more in details.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        quants = self.gather_relevant(self.product, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 2.0)

        move1._do_unreserve()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 0.0)
        self.assertEqual(len(move1.move_line_ids), 0.0)

    def test_unreserve_4(self):
        """ Check the unreservation of a partially available stock move.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        quants = self.gather_relevant(self.product, self.stock_location)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 2.0)

        move1._do_unreserve()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(len(quants), 1.0)
        self.assertEqual(quants.quantity, 2.0)
        self.assertEqual(quants.reserved_quantity, 0.0)
        self.assertEqual(len(move1.move_line_ids), 0.0)

    def test_unreserve_5(self):
        """ Check the unreservation of a stock move reserved on multiple quants.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 3)
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 2,
        })
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 5)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_unreserve_5',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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

        quants = self.gather_relevant(self.product, self.stock_location)
        self.assertEqual(len(quants), 2.0)
        for quant in quants:
            self.assertEqual(quant.reserved_quantity, 0)

    def test_unreserve_6(self):
        """ In a situation with a negative and a positive quant, reserve and unreserve.
        """
        q1 = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': -10,
            'reserved_quantity': 0,
        })

        q2 = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'quantity': 30.0,
            'reserved_quantity': 10.0,
        })

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 10.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_unreserve_6',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)
        self.assertEqual(move1.move_line_ids.product_qty, 10)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(q2.reserved_quantity, 20)

        move1._do_unreserve()
        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(len(move1.move_line_ids), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 10.0)
        self.assertEqual(q2.reserved_quantity, 10)

    def test_unreserve_7(self):
        """ Check the unreservation of a stock move delete only stock move lines
        without quantity done.
        """
        product = self.env['product.product'].create({
            'name': 'product',
            'tracking': 'serial',
            'type': 'product',
        })

        serial_numbers = self.env['stock.production.lot'].create([{
            'name': str(x),
            'product_id': product.id,
            'company_id': self.env.company.id,
        } for x in range(5)])

        for serial in serial_numbers:
            self.env['stock.quant'].create({
                'product_id': product.id,
                'location_id': self.stock_location.id,
                'quantity': 1.0,
                'lot_id': serial.id,
                'reserved_quantity': 0.0,
            })

        move1 = self.env['stock.move'].create({
            'name': 'test_unreserve_7',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 5.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 5)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, self.stock_location), 0.0)

        # Check state is changed even with 0 move lines unlinked
        move1.move_line_ids.write({'qty_done': 1})
        move1._do_unreserve()
        self.assertEqual(len(move1.move_line_ids), 5)
        self.assertEqual(move1.state, 'confirmed')
        move1._action_assign()
        # set a quantity done on the two first move lines
        move1.move_line_ids.write({'qty_done': 0})
        move1.move_line_ids[0].qty_done = 1
        move1.move_line_ids[1].qty_done = 1

        move1._do_unreserve()
        self.assertEqual(move1.state, 'confirmed')
        self.assertEqual(len(move1.move_line_ids), 2)
        self.assertEqual(move1.move_line_ids.mapped('qty_done'), [1, 1])
        self.assertEqual(move1.move_line_ids.mapped('product_uom_qty'), [0, 0])

    def test_link_assign_1(self):
        """ Test the assignment mechanism when two chained stock moves try to move one unit of an
        untracked product.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)

        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot1)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location, lot1)), 1.0)

        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_2_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_2_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})

        (move_stock_pack + move_pack_cust)._action_confirm()
        move_stock_pack._action_assign()

        move_line_stock_pack = move_stock_pack.move_line_ids[0]
        self.assertEqual(move_line_stock_pack.lot_id.id, lot1.id)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location, lot1)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.pack_location, lot1)), 0.0)

        move_line_stock_pack.qty_done = 1.0
        move_stock_pack._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location, lot1)), 0.0)

        move_line_pack_cust = move_pack_cust.move_line_ids[0]
        self.assertEqual(move_line_pack_cust.lot_id.id, lot1.id)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.pack_location, lot_id=lot1), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.pack_location, lot1)), 1.0)

    def test_link_assign_3(self):
        """ Test the assignment mechanism when three chained stock moves (2 sources, 1 dest) try to
        move multiple units of an untracked product.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)

        move_stock_pack_1 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_stock_pack_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.pack_location)), 1.0)

        move_stock_pack_2._action_assign()
        self.assertEqual(move_stock_pack_2.state, 'assigned')
        self.assertEqual(len(move_stock_pack_2.move_line_ids), 1)
        move_stock_pack_2.move_line_ids[0].qty_done = 1.0
        move_stock_pack_2._action_done()
        self.assertEqual(move_stock_pack_2.state, 'done')

        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.pack_location)), 1.0)

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
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2.0, lot_id=lot1)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location, lot1)), 1.0)

        move_stock_pack_1 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_stock_pack_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2.0)

        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move_pack_cust_1 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_pack_cust_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move_supp_stock_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_6_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move_stock_stock_1 = self.env['stock.move'].create({
            'name': 'test_link_assign_6_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move_stock_stock_1.write({'move_orig_ids': [(4, move_supp_stock_1.id, 0), (4, move_supp_stock_2.id, 0)]})
        move_stock_stock_2 = self.env['stock.move'].create({
            'name': 'test_link_assign_6_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move_stock_stock_2.write({'move_orig_ids': [(4, move_supp_stock_1.id, 0), (4, move_supp_stock_2.id, 0)]})

        (move_supp_stock_1 + move_supp_stock_2 + move_stock_stock_1 + move_stock_stock_2)._action_confirm()
        move_supp_stock_1._action_assign()
        self.assertEqual(move_supp_stock_1.state, 'assigned')
        self.assertEqual(move_supp_stock_2.state, 'assigned')
        self.assertEqual(move_stock_stock_1.state, 'waiting')
        self.assertEqual(move_stock_stock_2.state, 'waiting')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

        # do the fist move, it'll bring 3 units in stock location so only `move_stock_stock_1`
        # should be assigned
        move_supp_stock_1.move_line_ids.qty_done = 3.0
        move_supp_stock_1._action_done()
        self.assertEqual(move_supp_stock_1.state, 'done')
        self.assertEqual(move_supp_stock_2.state, 'assigned')
        self.assertEqual(move_stock_stock_1.state, 'assigned')
        self.assertEqual(move_stock_stock_2.state, 'waiting')

    def test_link_assign_7(self):
        # on the dozen uom, set the rounding set 1.0
        self.uom_dozen.rounding = 1

        # 6 units are available in stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 6.0)

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
            'product_id': self.product.id,
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
            'product_id': self.product.id,
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
            'product_id': self.product.id,
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
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
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
            'product_id': self.product.id,
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
        backorder.button_validate()
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
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, move_stock_pack.location_dest_id), 6)

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
                'product_id': self.product_serial.id,
                'company_id': self.env.company.id,
            })
            self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot_id)

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
            'product_id': self.product_serial.id,
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
            'product_id': self.product_serial.id,
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
                'product_id': self.product_serial.id,
                'company_id': self.env.company.id,
            })
            self.env['stock.quant']._update_available_quantity(self.product_serial, self.stock_location, 1.0, lot_id=lot_id)

        picking_stock_pack = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,
        })
        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_9',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product_serial.id,
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
            'product_id': self.product_serial.id,
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
        backorder_wizard = self.env[(res_dict_for_back_order.get('res_model'))].browse(res_dict_for_back_order.get('res_id')).with_context(res_dict_for_back_order['context'])
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
            'product_id': self.product_serial.id,
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

        backorder.button_validate()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.customer_location), 3)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_serial, self.pack_location), 0)

    def test_link_assign_10(self):
        """ Test the assignment mechanism with partial availability.
        """
        # make some stock:
        #   stock location: 2.0
        #   pack location: -1.0
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 1.0)

        move_out = self.env['stock.move'].create({
            'name': 'test_link_assign_out',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move_out._action_confirm()
        move_out._action_assign()
        move_out.quantity_done = 1.0
        move_out._action_done()
        self.assertEqual(len(self.gather_relevant(self.product, self.pack_location)), 1.0)

        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_assign_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_assign_1_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 10.0)
        move1 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 0.0,
            'quantity_done': 1.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3._action_done()
        self.assertEqual(move3.state, 'done')
        quant = self.env['stock.quant']._gather(self.product, self.stock_location)
        self.assertEqual(quant.quantity, 9.0)
        self.assertEqual(quant.reserved_quantity, 9.0)

    def test_use_reserved_move_line_2(self):
        # make 12 units available in stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 12.0)

        # reserve 12 units
        move1 = self.env['stock.move'].create({
            'name': 'test_use_reserved_move_line_2_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        quant = self.env['stock.quant']._gather(self.product, self.stock_location)
        self.assertEqual(quant.quantity, 12)
        self.assertEqual(quant.reserved_quantity, 12)

        # force a move of 1 dozen
        move2 = self.env['stock.move'].create({
            'name': 'test_use_reserved_move_line_2_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1,
        })
        move2._action_confirm()
        move2._action_assign()
        self.assertEqual(move2.state, 'confirmed')
        move2._set_quantity_done(1)
        move2._action_done()

        # mov1 should be unreserved and the quant should be unlinked
        self.assertEqual(move1.state, 'confirmed')
        quant = self.env['stock.quant']._gather(self.product, self.stock_location)
        self.assertEqual(quant.quantity, 0)
        self.assertEqual(quant.reserved_quantity, 0)

    def test_use_unreserved_move_line_1(self):
        """ Test that validating a stock move linked to an untracked product reserved by another one
        correctly unreserves the other one.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)

        # prepare the conflicting move
        move1 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })

        # reserve those move
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        move2._action_confirm()
        move2._action_assign()
        self.assertEqual(move2.state, 'confirmed')

        # use the product from the first one
        move2.write({'move_line_ids': [(0, 0, {
            'product_id': self.product.id,
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
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

    def test_use_unreserved_move_line_2(self):
        """ Test that validating a stock move linked to a tracked product reserved by another one
        correctly unreserves the other one.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })

        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot1)

        # prepare the conflicting move
        move1 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })

        # reserve those move
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 1.0)
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        move2._action_confirm()
        move2._action_assign()
        self.assertEqual(move2.state, 'confirmed')

        # use the product from the first one
        move2.write({'move_line_ids': [(0, 0, {
            'product_id': self.product.id,
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
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 0.0)

    def test_use_unreserved_move_line_3(self):
        """ Test the behavior of `_free_reservation` when ran on a recordset of move lines where
        some are assigned and some are force assigned. `_free_reservation` should not use an
        already processed move line when looking for a move line candidate to unreserve.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_use_unreserved_move_line_3',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.quantity_done = 1

        # add a forced move line in `move1`
        move1.write({'move_line_ids': [(0, 0, {
            'product_id': self.product.id,
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

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.customer_location), 3.0)

    def test_use_unreserved_move_line_4(self):
        product_01 = self.env['product.product'].create({
            'name': 'Product 01',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        product_02 = self.env['product.product'].create({
            'name': 'Product 02',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.env['stock.quant']._update_available_quantity(product_01, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(product_02, self.stock_location, 1)

        customer = self.env['res.partner'].create({'name': 'SuperPartner'})
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': customer.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })

        p01_move = self.env['stock.move'].create({
            'name': 'SuperMove01',
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'picking_id': picking.id,
            'product_id': product_01.id,
            'product_uom_qty': 1,
            'product_uom': product_01.uom_id.id,
        })
        self.env['stock.move'].create({
            'name': 'SuperMove02',
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'picking_id': picking.id,
            'product_id': product_02.id,
            'product_uom_qty': 1,
            'product_uom': product_02.uom_id.id,
        })

        picking.action_confirm()
        picking.action_assign()
        p01_move.product_uom_qty = 0
        picking.do_unreserve()
        picking.action_assign()
        p01_move.product_uom_qty = 1
        self.assertEqual(p01_move.state, 'confirmed')

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
        self.env['stock.quant']._update_available_quantity(self.product, shelf1_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.product, shelf2_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

    def test_edit_reserved_move_line_2(self):
        """ Test that editing a stock move line linked to a tracked product correctly and directly
        adapts the reservation. In this case, we edit the lot to another available one.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 1.0)

        move1.move_line_ids.lot_id = lot2.id

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 0.0)

    def test_edit_reserved_move_line_3(self):
        """ Test that editing a stock move line linked to a packed product correctly and directly
        adapts the reservation. In this case, we edit the package to another available one.
        """
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_3'})
        package2 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_3'})

        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, package_id=package2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package2), 1.0)

        move1.move_line_ids.package_id = package2.id

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package2), 0.0)

    def test_edit_reserved_move_line_4(self):
        """ Test that editing a stock move line linked to an owned product correctly and directly
        adapts the reservation. In this case, we edit the owner to another available one.
        """
        owner1 = self.env['res.partner'].create({'name': 'test_edit_reserved_move_line_4_1'})
        owner2 = self.env['res.partner'].create({'name': 'test_edit_reserved_move_line_4_2'})

        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, owner_id=owner1)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, owner_id=owner2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner2), 1.0)

        move1.move_line_ids.owner_id = owner2.id

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner2), 0.0)

    def test_edit_reserved_move_line_5(self):
        """ Test that editing a stock move line linked to a packed and tracked product correctly
        and directly adapts the reservation. In this case, we edit the lot to another available one
        that is not in a pack.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_5'})

        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot1, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 1.0)
        move_line = move1.move_line_ids[0]
        move_line.write({'package_id': False, 'lot_id': lot2.id})

        self.assertEqual(move1.reserved_availability, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 0.0)

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
        self.env['stock.quant']._update_available_quantity(self.product, shelf1_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.move_line_ids.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(move1.move_line_ids.state, 'confirmed')
        self.assertEqual(move1.reserved_availability, 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)

    def test_edit_reserved_move_line_7(self):
        """ Send 5 tracked products to a client, but these products do not have any lot set in our
        inventory yet: we only set them at delivery time. The created move line should have 5 items
        without any lot set, if we edit to set them to lot1, the reservation should not change.
        Validating the stock move should should not create a negative quant for this lot in stock
        location.
        # """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        # make some stock without assigning a lot id
        self.env['stock.quant']._update_available_quantity(self.product_lot, self.stock_location, 5)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_lot.id,
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

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product_lot, self.stock_location)), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product_lot, self.stock_location, lot_id=lot1, strict=True)), 0.0)

    def test_edit_reserved_move_line_8(self):
        """ Send 5 tracked products to a client, but some of these products do not have any lot set
        in our inventory yet: we only set them at delivery time. Adding a lot_id on the move line
        that does not have any should not change its reservation, and validating should not create
        a negative quant for this lot in stock.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        # make some stock without assigning a lot id
        self.env['stock.quant']._update_available_quantity(self.product_lot, self.stock_location, 3)
        self.env['stock.quant']._update_available_quantity(self.product_lot, self.stock_location, 2, lot_id=lot1)

        # creation
        move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product_lot.id,
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

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot1, strict=True), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot2, strict=True), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product_lot, self.stock_location)), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product_lot, self.stock_location, lot_id=lot1, strict=True)), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product_lot, self.stock_location, lot_id=lot2, strict=True)), 0.0)

    def test_edit_reserved_move_line_9(self):
        """
        When writing on the reserved quantity on the SML, a process tries to
        reserve the quants with that new quantity. If it fails (for instance
        because the written quantity is more than actually available), this
        quantity should be reset to 0.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0)

        out_move = self.env['stock.move'].create({
            'name': self.product.name,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
        })
        out_move._action_confirm()
        out_move._action_assign()

        # try to manually assign more than available
        out_move.move_line_ids.product_uom_qty = 2

        self.assertTrue(out_move.move_line_ids)
        self.assertEqual(out_move.move_line_ids.product_uom_qty, 0, "The reserved quantity should be cancelled")

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
        self.env['stock.quant']._update_available_quantity(self.product, shelf1_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.product, shelf2_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)

        # move from shelf1
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

        # edit once done, we actually moved from shelf2
        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

    def test_edit_done_move_line_2(self):
        """ Test that editing a done stock move line linked to a tracked product correctly and directly
        adapts the transfer. In this case, we edit the lot to another available one.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 1.0)

        move1.move_line_ids.lot_id = lot2.id

        # reserved_availability should always been 0 for done move.
        self.assertEqual(move1.reserved_availability, 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 0.0)

    def test_edit_done_move_line_3(self):
        """ Test that editing a done stock move line linked to a packed product correctly and directly
        adapts the transfer. In this case, we edit the package to another available one.
        """
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_3'})
        package2 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_3'})

        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, package_id=package2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package2), 1.0)

        move1.move_line_ids.package_id = package2.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, package_id=package2), 0.0)

    def test_edit_done_move_line_4(self):
        """ Test that editing a done stock move line linked to an owned product correctly and directly
        adapts the transfer. In this case, we edit the owner to another available one.
        """
        owner1 = self.env['res.partner'].create({'name': 'test_edit_reserved_move_line_4_1'})
        owner2 = self.env['res.partner'].create({'name': 'test_edit_reserved_move_line_4_2'})

        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, owner_id=owner1)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, owner_id=owner2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner2), 1.0)

        move1.move_line_ids.owner_id = owner2.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, owner_id=owner2), 0.0)

    def test_edit_done_move_line_5(self):
        """ Test that editing a done stock move line linked to a packed and tracked product correctly
        and directly adapts the transfer. In this case, we edit the lot to another available one
        that is not in a pack.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_5'})

        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot1, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1.0, lot_id=lot2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 1.0)
        move_line = move1.move_line_ids[0]
        move_line.write({'package_id': False, 'lot_id': lot2.id})

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot1, package_id=package1), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, lot_id=lot2), 0.0)

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
        self.env['stock.quant']._update_available_quantity(self.product, shelf1_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location, allow_negative=True), -1.0)

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
        self.env['stock.quant']._update_available_quantity(self.product, shelf1_location, 1.0)
        self.env['stock.quant']._update_available_quantity(self.product, shelf2_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 1.0)

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2._action_confirm()
        move2._action_assign()

        self.assertEqual(move2.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

        move1.move_line_ids.location_id = shelf2_location.id

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf2_location), 0.0)
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
        self.env['stock.quant']._update_available_quantity(self.product, shelf1_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

        # move from shelf1
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(move1.product_uom_qty, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

        # edit once done, we actually moved 2 products
        move1.move_line_ids.qty_done = 2

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location, allow_negative=True), -1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location, allow_negative=True), -1.0)
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
        self.env['stock.quant']._update_available_quantity(self.product, shelf1_location, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

        # move from shelf1
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self.assertEqual(move1.product_uom_qty, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)

        # edit once done, we actually moved 2 products
        move1.move_line_ids.qty_done = 0

        self.assertEqual(move1.product_uom_qty, 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, shelf1_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 1.0)

    def test_edit_done_move_line_10(self):
        """ Edit the quantity done for an incoming move shoudld also remove the quant if there
            are no product in stock.
        """
        # move from shelf1
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10
        move1._action_done()

        quant = self.gather_relevant(self.product, self.stock_location)
        self.assertEqual(len(quant), 1.0)

        # edit once done, we actually moved 2 products
        move1.move_line_ids.qty_done = 0

        quant = self.gather_relevant(self.product, self.stock_location)
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.action_assign()
        move1.move_line_ids.qty_done = 10
        picking._action_done()
        self.assertEqual(move1.product_uom_qty, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 10.0)
        self.env['stock.move.line'].create({
            'picking_id': move1.move_line_ids.picking_id.id,
            'move_id': move1.move_line_ids.move_id.id,
            'product_id': move1.move_line_ids.product_id.id,
            'qty_done': move1.move_line_ids.qty_done,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.move_line_ids.location_id.id,
            'location_dest_id': move1.move_line_ids.location_dest_id.id,
        })
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 20.0)
        move1.move_line_ids[1].qty_done = 5
        self.assertEqual(move1.product_uom_qty, 15.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 15.0)

    def test_edit_done_move_line_12(self):
        """ Test that editing a done stock move line linked a tracked product correctly and directly
        adapts the transfer. In this case, we edit the lot to another one, but the original move line
        is not in the default product's UOM.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_done_move_line_12'})
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product_lot.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1.move_line_ids.lot_id = lot1.id
        move1._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot1), 12.0)

        # Change the done quantity from 1 dozen to two dozen
        move1.move_line_ids.qty_done = 2
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot1), 24.0)

    def test_edit_done_move_line_13(self):
        """ Test that editing a done stock move line linked to a packed and tracked product correctly
        and directly adapts the transfer. In this case, we edit the lot to another available one
        that we put in the same pack.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        package1 = self.env['stock.quant.package'].create({'name': 'test_edit_reserved_move_line_5'})

        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product_lot.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1
        move1.move_line_ids.lot_id = lot1.id
        move1.move_line_ids.result_package_id = package1.id
        move1._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot1, package_id=package1), 1.0)

        move1.move_line_ids.write({'lot_id': lot2.id})

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot1, package_id=package1), 0.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_lot, self.stock_location, lot_id=lot2, package_id=package1), 1.0)

    def test_edit_done_move_line_14(self):
        """ Test that editing a done stock move line with a different UoM from its stock move correctly
        updates the quant when its qty and/or its UoM is edited. Also check that we don't allow editing
        a done stock move's UoM.
        """
        move1 = self.env['stock.move'].create({
            'name': 'test_edit_moveline',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.product_uom_id = self.uom_dozen
        move1.move_line_ids.qty_done = 1
        move1._action_done()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 12.0)

        move1.move_line_ids.qty_done = 2
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 24.0)
        self.assertEqual(move1.product_uom_qty, 24.0)
        self.assertEqual(move1.product_qty, 24.0)

        move1.move_line_ids.product_uom_id = self.uom_unit
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 2.0)
        self.assertEqual(move1.product_uom_qty, 2.0)
        self.assertEqual(move1.product_qty, 2.0)

        with self.assertRaises(UserError):
            move1.product_uom = self.uom_dozen

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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.action_assign()
        res_dict = picking.button_validate()
        self.assertEqual(res_dict.get('res_model'), 'stock.immediate.transfer')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 10.0)

    def test_immediate_validate_2(self):
        """ In a picking with a single partially available move, clicking on validate without
        filling any quantities should open a wizard asking to process all the reservation (so, only
        a part of the initial demand). Validating this wizard should open another one asking for
        the creation of a backorder. If the backorder is created, it should contain the quantities
        not processed.
        """
        partner = self.env['res.partner'].create({'name': 'Jean'})
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 5.0)
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.action_assign()
        # Only 5 products are reserved on the move of 10, click on `button_validate`.
        res_dict = picking.button_validate()
        self.assertEqual(res_dict.get('res_model'), 'stock.immediate.transfer')
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        res_dict_for_back_order = wizard.process()
        self.assertEqual(res_dict_for_back_order.get('res_model'), 'stock.backorder.confirmation')
        backorder_wizard = self.env[(res_dict_for_back_order.get('res_model'))].browse(res_dict_for_back_order.get('res_id')).with_context(res_dict_for_back_order['context'])
        # Chose to create a backorder.
        backorder_wizard.process()

        # Only 5 products should be processed on the initial move.
        self.assertEqual(picking.move_lines.state, 'done')
        self.assertEqual(picking.move_lines.quantity_done, 5.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 0.0)

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

        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1)

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
            'product_id': self.product.id,
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
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        action = wizard.process()
        self.assertTrue(isinstance(action, dict), 'Should open backorder wizard')
        self.assertEqual(action.get('res_model'), 'stock.backorder.confirmation')
        wizard = self.env[(action.get('res_model'))].browse(action.get('res_id')).with_context(action.get('context'))
        wizard.process()
        backorder = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
        self.assertEqual(len(backorder), 1.0)

        # The backorder should contain 99 product1 and 100 product5.
        for backorder_move in backorder.move_lines:
            if backorder_move.product_id.id == self.product.id:
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
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_lot, self.stock_location, 5.0, lot_id=lot1)
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
            'product_id': self.product_lot.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        picking.action_confirm()
        picking.action_assign()
        # No quantities filled, immediate transfer wizard should pop up.
        immediate_trans_wiz_dict = picking.button_validate()
        self.assertEqual(immediate_trans_wiz_dict.get('res_model'), 'stock.immediate.transfer')
        immediate_trans_wiz = Form(self.env[immediate_trans_wiz_dict['res_model']].with_context(immediate_trans_wiz_dict['context'])).save()
        immediate_trans_wiz.process()

        self.assertEqual(picking.move_lines.quantity_done, 5.0)
        # Check move_lines data
        self.assertEqual(len(picking.move_lines.move_line_ids), 1)
        self.assertEqual(picking.move_lines.move_line_ids.lot_id, lot1)
        self.assertEqual(picking.move_lines.move_line_ids.qty_done, 5.0)
        # Check quants data
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0.0)
        self.assertEqual(len(self.gather_relevant(self.product, self.stock_location)), 0.0)

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
        product_id = self.product_serial
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
        })
        product3_move = self.env['stock.move'].create({
            'name': 'product3_move',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_id': picking.id,
            'product_id': self.product_lot.id,
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        picking.action_confirm()
        picking.action_assign()

        scrap = self.env['stock.scrap'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'product_uom_id': self.uom_unit.id,
            'scrap_qty': 5.0,
        })
        scrap.do_scrap()

        # No products are reserved on the move of 10, click on `button_validate`.
        with self.assertRaises(UserError):
            picking.button_validate()

    def test_immediate_validate_8(self):
        """Validate three receipts at once."""
        partner = self.env['res.partner'].create({'name': 'Pierre'})
        receipt1 = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        self.env['stock.move'].create({
            'name': 'test_immediate_validate_8_1',
            'location_id': receipt1.location_id.id,
            'location_dest_id': receipt1.location_dest_id.id,
            'picking_id': receipt1.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        receipt1.action_confirm()
        receipt2 = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        self.env['stock.move'].create({
            'name': 'test_immediate_validate_8_2',
            'location_id': receipt2.location_id.id,
            'location_dest_id': receipt2.location_dest_id.id,
            'picking_id': receipt2.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        receipt2.action_confirm()
        receipt3 = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        self.env['stock.move'].create({
            'name': 'test_immediate_validate_8_3',
            'location_id': receipt3.location_id.id,
            'location_dest_id': receipt3.location_dest_id.id,
            'picking_id': receipt3.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        receipt3.action_confirm()

        immediate_trans_wiz_dict = (receipt1 + receipt2).button_validate()
        immediate_trans_wiz = Form(self.env[immediate_trans_wiz_dict['res_model']].with_context(immediate_trans_wiz_dict['context'])).save()
        # The different transfers are displayed to the users.
        self.assertTrue(immediate_trans_wiz.show_transfers)
        # All transfers are processed by default
        self.assertEqual(immediate_trans_wiz.immediate_transfer_line_ids.mapped('to_immediate'), [True, True])
        # Only transfer receipt1
        immediate_trans_wiz.immediate_transfer_line_ids.filtered(lambda line: line.picking_id == receipt2).to_immediate = False
        immediate_trans_wiz.process()
        self.assertEqual(receipt1.state, 'done')
        self.assertEqual(receipt2.state, 'assigned')
        # Transfer receipt2 and receipt3.
        immediate_trans_wiz_dict = (receipt3 + receipt2).button_validate()
        immediate_trans_wiz = Form(self.env[immediate_trans_wiz_dict['res_model']].with_context(immediate_trans_wiz_dict['context'])).save()
        immediate_trans_wiz.process()
        self.assertEqual(receipt2.state, 'done')
        self.assertEqual(receipt3.state, 'done')

    def test_set_quantity_done_1(self):
        move1 = self.env['stock.move'].create({
            'name': 'test_set_quantity_done_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_set_quantity_done_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
        })
        self.assertEqual(move1.state, 'draft')
        self.assertEqual(move1.product_uom_qty, 1)
        move1.product_uom_qty = 100
        move1.product_id = self.product_serial
        move1._onchange_product_id()
        self.assertEqual(move1.product_uom_qty, 100)

    def test_scrap_1(self):
        """ Check the created stock move and the impact on quants when we scrap a
        storable product.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1)
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product.id,
            'product_uom_id':self.product.uom_id.id,
            'scrap_qty': 1,
        })
        scrap.do_scrap()
        self.assertEqual(scrap.state, 'done')
        move = scrap.move_id
        self.assertEqual(move.state, 'done')
        self.assertEqual(move.quantity_done, 1)
        self.assertEqual(move.scrapped, True)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0)

    def test_scrap_2(self):
        """ Check the created stock move and the impact on quants when we scrap a
        consumable product.
        """
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product_consu.id,
            'product_uom_id':self.product_consu.uom_id.id,
            'scrap_qty': 1,
        })
        self.assertEqual(scrap.name, 'New', 'Name should be New in draft state')
        scrap.do_scrap()
        self.assertTrue(scrap.name.startswith('SP/'), 'Sequence should be Changed after do_scrap')
        self.assertEqual(scrap.state, 'done')
        move = scrap.move_id
        self.assertEqual(move.state, 'done')
        self.assertEqual(move.quantity_done, 1)
        self.assertEqual(move.scrapped, True)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_consu, self.stock_location), 0)

    def test_scrap_3(self):
        """ Scrap the product of a reserved move line. Check that the move line is
        correctly deleted and that the associated stock move is not assigned anymore.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1)
        move1 = self.env['stock.move'].create({
            'name': 'test_scrap_3',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(len(move1.move_line_ids), 1)

        scrap = self.env['stock.scrap'].create({
            'product_id': self.product.id,
            'product_uom_id':self.product.uom_id.id,
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
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 10)
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_id': picking.id,
        })
        move1._action_confirm()

        self.assertEqual(move1.state, 'assigned')
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
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
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 4)

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
            'product_id': self.product.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1.0,
            'picking_id': picking.id,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.reserved_availability, 0.33)

        # scrap a unit
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'scrap_qty': 1,
            'picking_id': picking.id,
        })
        scrap.action_validate()

        self.assertEqual(scrap.state, 'done')
        self.assertEqual(move1.reserved_availability, 0.25)

    def test_scrap_6(self):
        """ Check that scrap correctly handle UoM. """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1)
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product.id,
            'product_uom_id': self.uom_dozen.id,
            'scrap_qty': 1,
        })
        warning_message = scrap.action_validate()
        self.assertEqual(warning_message.get('res_model', 'Wrong Model'), 'stock.warn.insufficient.qty.scrap')
        insufficient_qty_wizard = self.env['stock.warn.insufficient.qty.scrap'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'scrap_id': scrap.id,
            'quantity': 1,
            'product_uom_name': self.product.uom_id.name
        })
        insufficient_qty_wizard.action_done()
        self.assertEqual(self.env['stock.quant']._gather(self.product, self.stock_location).quantity, -11)

    def test_scrap_7_sn_warning(self):
        """ Check serial numbers are correctly double checked """

        child_loc1 = self.env['stock.location'].create({
            'name': "child_location1",
            'usage': 'internal',
            'location_id': self.stock_location.id
        })
        child_loc2 = self.env['stock.location'].create({
            'name': "child_location2",
            'usage': 'internal',
            'location_id': self.stock_location.id
        })

        lot1 = self.env['stock.production.lot'].create({
            'name': 'serial1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(self.product_serial, child_loc1, 1, lot1)

        scrap = self.env['stock.scrap'].create({
            'product_id': self.product_serial.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': child_loc2.id,
            'lot_id': lot1.id
        })

        warning = False
        warning = scrap._onchange_serial_number()
        self.assertTrue(warning, 'Use of wrong serial number location not detected')
        self.assertEqual(list(warning.keys())[0], 'warning', 'Warning message was not returned')
        self.assertEqual(scrap.location_id, child_loc1, 'Location was not auto-corrected')

    def test_scrap_8(self):
        """
        Suppose a user wants to scrap some products thanks to internal moves.
        This test checks the state of the picking based on few cases
        """
        scrap_location = self.env['stock.location'].search([('company_id', '=', self.env.company.id), ('scrap_location', '=', True)], limit=1)
        internal_operation = self.env['stock.picking.type'].with_context(active_test=False).search([('code', '=', 'internal'), ('company_id', '=', self.env.company.id)], limit=1)
        internal_operation.active = True

        product01 = self.product
        product02 = self.env['product.product'].create({
            'name': 'SuperProduct',
            'type': 'product',
        })

        self.env['stock.quant']._update_available_quantity(product01, self.stock_location, 3)
        self.env['stock.quant']._update_available_quantity(product02, self.stock_location, 1)

        scrap_picking01, scrap_picking02, scrap_picking03 = self.env['stock.picking'].create([{
            'location_id': self.stock_location.id,
            'location_dest_id': scrap_location.id,
            'picking_type_id': internal_operation.id,
            'move_lines': [(0, 0, {
                'name': 'Scrap %s' % product.display_name,
                'location_id': self.stock_location.id,
                'location_dest_id': scrap_location.id,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': 1.0,
                'picking_type_id': internal_operation.id,
            }) for product in products],
        } for products in [(product01,), (product01,), (product01, product02)]])

        (scrap_picking01 + scrap_picking02 + scrap_picking03).action_confirm()

        # All SM are processed
        scrap_picking01.move_lines.quantity_done = 1
        scrap_picking01.button_validate()

        # All SM are cancelled
        scrap_picking02.action_cancel()

        # Process one SM and cancel the other one
        pick03_prod01_move = scrap_picking03.move_lines.filtered(lambda sm: sm.product_id == product01)
        pick03_prod02_move = scrap_picking03.move_lines - pick03_prod01_move
        pick03_prod01_move.quantity_done = 1
        pick03_prod02_move._action_cancel()
        scrap_picking03.button_validate()

        self.assertEqual(scrap_picking01.move_lines.state, 'done')
        self.assertEqual(scrap_picking01.state, 'done')

        self.assertEqual(scrap_picking02.move_lines.state, 'cancel')
        self.assertEqual(scrap_picking02.state, 'cancel')

        self.assertEqual(pick03_prod01_move.state, 'done')
        self.assertEqual(pick03_prod02_move.state, 'cancel')
        self.assertEqual(scrap_picking03.state, 'done')

        self.assertEqual(self.env['stock.quant']._get_available_quantity(product01, self.stock_location), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product02, self.stock_location), 1)

    def test_in_date_1(self):
        """ Check that moving a tracked quant keeps the incoming date.
        """
        move1 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product_lot.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.lot_name = 'lot1'
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        quant = self.gather_relevant(self.product_lot, self.stock_location)
        self.assertEqual(len(quant), 1.0)
        self.assertNotEqual(quant.in_date, False)

        # Keep a reference to the initial incoming date in order to compare it later.
        initial_incoming_date = quant.in_date

        move2 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product_lot.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 1
        move2._action_done()

        quant = self.gather_relevant(self.product_lot, self.pack_location)
        self.assertEqual(len(quant), 1.0)
        self.assertEqual(quant.in_date, initial_incoming_date)

    def test_in_date_2(self):
        """ Check that editing a done move line for a tracked product and changing its lot
        correctly restores the original lot with its incoming date and remove the new lot
        with its incoming date.
        """
        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        # receive lot1
        move1 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product_lot.id,
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
            'product_id': self.product_lot.id,
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
            ('product_id', '=', self.product_lot.id),
            ('lot_id', '=', lot2.id),
        ]).in_date

        # Edit lot1's incoming date.
        quant_lot1 = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product_lot.id),
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
            'product_id': self.product_lot.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 1
        move3._action_done()
        quant_in_pack = self.env['stock.quant'].search([
            ('product_id', '=', self.product_lot.id),
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
            ('product_id', '=', self.product_lot.id),
            ('lot_id', '=', lot1.id),
            ('quantity', '!=', 0),
        ])
        self.assertEqual(quant_lot1.location_id, self.stock_location)
        self.assertAlmostEqual(quant_lot1.in_date, initial_in_date_lot1, delta=timedelta(seconds=1))

        # Check that lo2 is in pack with is right in_date
        quant_lot2 = self.env['stock.quant'].search([
            ('location_id.usage', '=', 'internal'),
            ('product_id', '=', self.product_lot.id),
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
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': self.product_lot.id,
            'company_id': self.env.company.id,
        })
        # receive lot1
        move1 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product_lot.id,
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
            'product_id': self.product_lot.id,
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
            ('product_id', '=', self.product_lot.id),
            ('lot_id', '=', lot2.id),
            ('quantity', '!=', 0),
        ]).in_date

        # Edit lot1's incoming date.
        quant_lot1 = self.env['stock.quant'].search([
            ('location_id.usage', '=', 'internal'),
            ('product_id', '=', self.product_lot.id),
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
            'product_id': self.product_lot.id,
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
            ('product_id', '=', self.product_lot.id),
            ('quantity', '!=', 0),
        ])
        self.assertEqual(len(quants), 2)
        for quant in quants:
            if quant.lot_id == lot1:
                self.assertAlmostEqual(quant.in_date, initial_in_date_lot1, delta=timedelta(seconds=1))
            elif quant.lot_id == lot2:
                self.assertAlmostEqual(quant.in_date, initial_in_date_lot2, delta=timedelta(seconds=1))

    def test_edit_initial_demand_1(self):
        """ Increase initial demand once everything is reserved and check if
        the existing move_line is updated.
        """
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
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
            'product_id': self.product.id,
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
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'quantity_done': 10.0,
            'picking_id': picking.id,
        })
        picking._autoconfirm_picking()
        self.assertEqual(picking.state, 'assigned')
        move1.quantity_done = 12
        self.assertEqual(picking.state, 'assigned')

    def test_initial_demand_4(self):
        """ Increase the initial demand on a delivery picking, the system should not automatically
        reserve the new quantity.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 12)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
        """ Changing type of an existing product will raise a user error if
            - some move are reserved
            - switching from a stockable product when qty_available is not zero
        """
        move_in = self.env['stock.move'].create({
            'name': 'test_customer',
            'location_id': self.customer_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move_in._action_confirm()
        move_in._action_assign()

        # Check raise UserError(_("You can not change the type of a product that is currently reserved on a stock
        with self.assertRaises(UserError):
            self.product.detailed_type = 'consu'
        move_in._action_cancel()

        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 10)

        # Check raise UserError(_("Available quantity should be set to zero before changing detailed_type"))
        with self.assertRaises(UserError):
            self.product.detailed_type = 'consu'

        move_out = self.env['stock.move'].create({
            'name': 'test_customer',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': self.product.qty_available,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move_out._action_confirm()
        move_out._action_assign()
        move_out.quantity_done = self.product.qty_available
        move_out._action_done()
        self.product.detailed_type = 'consu'

        move2 = self.env['stock.move'].create({
            'name': 'test_customer',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })

        move2._action_confirm()
        move2._action_assign()

        with self.assertRaises(UserError):
            self.product.detailed_type = 'product'
        move2._action_cancel()
        self.product.detailed_type = 'product'

    def test_edit_done_picking_1(self):
        """ Add a new move line in a done picking should generate an
        associated move.
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 12)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'picking_id': picking.id,
        })
        picking.action_confirm()
        picking.action_assign()
        move1.quantity_done = 10
        picking._action_done()

        self.assertEqual(len(picking.move_lines), 1, 'One move should exist for the picking.')
        self.assertEqual(len(picking.move_line_ids), 1, 'One move line should exist for the picking.')

        ml = self.env['stock.move.line'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
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
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 2)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'picking_id': picking.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0)
        move1.quantity_done = 1
        picking.action_put_in_pack()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0)
        self.assertEqual(len(picking.move_line_ids), 2)
        unpacked_ml = picking.move_line_ids.filtered(lambda ml: not ml.result_package_id)
        self.assertEqual(unpacked_ml.product_qty, 1)
        unpacked_ml.qty_done = 1
        picking.action_put_in_pack()
        self.assertEqual(len(picking.move_line_ids), 2)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0)
        picking.button_validate()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.customer_location), 2)

    def test_put_in_pack_2(self):
        """Check that reserving moves without done quantity
        adding in same package.
        """
        product1 = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(product1, self.stock_location, 2)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_id': picking.id,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_transit_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'picking_id': picking.id,
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, self.stock_location), 0)
        picking.action_put_in_pack()
        self.assertEqual(len(picking.move_line_ids), 2)
        self.assertEqual(picking.move_line_ids[0].qty_done, 1, "Stock move line should have 1 quantity as a done quantity.")
        self.assertEqual(picking.move_line_ids[1].qty_done, 2, "Stock move line should have 2 quantity as a done quantity.")
        line1_result_package = picking.move_line_ids[0].result_package_id
        line2_result_package = picking.move_line_ids[1].result_package_id
        self.assertEqual(line1_result_package, line2_result_package, "Product and Product1 should be in a same package.")

    def test_put_in_pack_3(self):
        """Check that one reserving move without done quantity and
        another reserving move with done quantity adding in different
        package.
        """
        product1 = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(product1, self.stock_location, 2)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'picking_id': picking.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_transit_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'picking_id': picking.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product1, self.stock_location), 0)
        move1.quantity_done = 1
        picking.action_put_in_pack()
        move2.quantity_done = 2
        picking.action_put_in_pack()
        self.assertEqual(len(picking.move_line_ids), 2)
        line1_result_package = picking.move_line_ids[0].result_package_id
        line2_result_package = picking.move_line_ids[1].result_package_id
        self.assertNotEqual(line1_result_package, line2_result_package, "Product and Product1 should be in a different package.")

    def test_move_line_aggregated_product_quantities(self):
        """ Test the `stock.move.line` method `_get_aggregated_product_quantities`,
        who returns data used to print delivery slips.
        """
        # Creates two other products.
        product2 = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        product3 = self.env['product.product'].create({
            'name': 'Product C',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        # Adds some quantity on stock.
        self.env['stock.quant'].with_context(inventory_mode=True).create([{
            'product_id': self.product.id,
            'inventory_quantity': 100,
            'location_id': self.stock_location.id,
        }, {
            'product_id': product2.id,
            'inventory_quantity': 100,
            'location_id': self.stock_location.id,
        }, {
            'product_id': product3.id,
            'inventory_quantity': 100,
            'location_id': self.stock_location.id,
        }]).action_apply_inventory()

        # Creates a delivery for a bunch of products.
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 10
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = product2
            move.product_uom_qty = 10
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = product3
            move.product_uom_qty = 10
        delivery = delivery_form.save()
        delivery.action_confirm()

        # Delivers a part of the quantity, creates a backorder for the remaining qty.
        delivery.move_line_ids.filtered(lambda ml: ml.product_id == self.product).qty_done = 6
        delivery.move_line_ids.filtered(lambda ml: ml.product_id == product2).qty_done = 2
        backorder_wizard_dict = delivery.button_validate()
        backorder_wizard_form = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context']))
        backorder_wizard_form.save().process()  # Creates the backorder.

        first_backorder = self.env['stock.picking'].search([('backorder_id', '=', delivery.id)], limit=1)
        # Checks the values.
        aggregate_values = delivery.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 2)
        sml1 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == self.product)
        sml2 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == product2)
        aggregate_val_1 = aggregate_values[f'{self.product.id}_{self.product.name}__{sml1.product_uom_id.id}']
        aggregate_val_2 = aggregate_values[f'{product2.id}_{product2.name}__{sml2.product_uom_id.id}']
        self.assertEqual(aggregate_val_1['qty_ordered'], 10)
        self.assertEqual(aggregate_val_1['qty_done'], 6)
        self.assertEqual(aggregate_val_2['qty_ordered'], 10)
        self.assertEqual(aggregate_val_2['qty_done'], 2)

        # Delivers a part of the BO's qty., and creates an another backorder.
        first_backorder.move_line_ids.filtered(lambda ml: ml.product_id == self.product).qty_done = 4
        first_backorder.move_line_ids.filtered(lambda ml: ml.product_id == product2).qty_done = 6
        first_backorder.move_line_ids.filtered(lambda ml: ml.product_id == product3).qty_done = 7
        backorder_wizard_dict = first_backorder.button_validate()
        backorder_wizard_form = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context']))
        backorder_wizard_form.save().process()  # Creates the backorder.

        second_backorder = self.env['stock.picking'].search([('backorder_id', '=', first_backorder.id)], limit=1)

        # Checks the values for the original delivery.
        aggregate_values = delivery.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 2)
        sml1 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == self.product)
        sml2 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == product2)
        aggregate_val_1 = aggregate_values[f'{self.product.id}_{self.product.name}__{sml1.product_uom_id.id}']
        aggregate_val_2 = aggregate_values[f'{product2.id}_{product2.name}__{sml2.product_uom_id.id}']
        self.assertEqual(aggregate_val_1['qty_ordered'], 10)
        self.assertEqual(aggregate_val_1['qty_done'], 6)
        self.assertEqual(aggregate_val_2['qty_ordered'], 10)
        self.assertEqual(aggregate_val_2['qty_done'], 2)
        # Checks the values for the first back order.
        aggregate_values = first_backorder.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 3)
        sml1 = first_backorder.move_line_ids.filtered(lambda ml: ml.product_id == self.product)
        sml2 = first_backorder.move_line_ids.filtered(lambda ml: ml.product_id == product2)
        sml3 = first_backorder.move_line_ids.filtered(lambda ml: ml.product_id == product3)
        aggregate_val_1 = aggregate_values[f'{self.product.id}_{self.product.name}__{sml1.product_uom_id.id}']
        aggregate_val_2 = aggregate_values[f'{product2.id}_{product2.name}__{sml2.product_uom_id.id}']
        aggregate_val_3 = aggregate_values[f'{product3.id}_{product3.name}__{sml3.product_uom_id.id}']
        self.assertEqual(aggregate_val_1['qty_ordered'], 4)
        self.assertEqual(aggregate_val_1['qty_done'], 4)
        self.assertEqual(aggregate_val_2['qty_ordered'], 8)
        self.assertEqual(aggregate_val_2['qty_done'], 6)
        self.assertEqual(aggregate_val_3['qty_ordered'], 10)
        self.assertEqual(aggregate_val_3['qty_done'], 7)

        # Delivers a part of the second BO's qty. but doesn't create a backorder this time.
        second_backorder.move_line_ids.filtered(lambda ml: ml.product_id == product3).qty_done = 3
        backorder_wizard_dict = second_backorder.button_validate()
        backorder_wizard_form = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context']))
        backorder_wizard_form.save().process_cancel_backorder()

        # Checks again the values for the original delivery.
        aggregate_values = delivery.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 2)
        sml1 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == self.product)
        sml2 = delivery.move_line_ids.filtered(lambda ml: ml.product_id == product2)
        aggregate_val_1 = aggregate_values[f'{self.product.id}_{self.product.name}__{sml1.product_uom_id.id}']
        aggregate_val_2 = aggregate_values[f'{product2.id}_{product2.name}__{sml2.product_uom_id.id}']
        self.assertEqual(aggregate_val_1['qty_ordered'], 10)
        self.assertEqual(aggregate_val_1['qty_done'], 6)
        self.assertEqual(aggregate_val_2['qty_ordered'], 10)
        self.assertEqual(aggregate_val_2['qty_done'], 2)
        # Checks again the values for the first back order.
        aggregate_values = first_backorder.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 3)
        sml1 = first_backorder.move_line_ids.filtered(lambda ml: ml.product_id == self.product)
        sml2 = first_backorder.move_line_ids.filtered(lambda ml: ml.product_id == product2)
        sml3 = first_backorder.move_line_ids.filtered(lambda ml: ml.product_id == product3)
        aggregate_val_1 = aggregate_values[f'{self.product.id}_{self.product.name}__{sml1.product_uom_id.id}']
        aggregate_val_2 = aggregate_values[f'{product2.id}_{product2.name}__{sml2.product_uom_id.id}']
        aggregate_val_3 = aggregate_values[f'{product3.id}_{product3.name}__{sml3.product_uom_id.id}']
        self.assertEqual(aggregate_val_1['qty_ordered'], 4)
        self.assertEqual(aggregate_val_1['qty_done'], 4)
        self.assertEqual(aggregate_val_2['qty_ordered'], 8)
        self.assertEqual(aggregate_val_2['qty_done'], 6)
        self.assertEqual(aggregate_val_3['qty_ordered'], 10)
        self.assertEqual(aggregate_val_3['qty_done'], 7)
        # Checks the values for the second back order.
        aggregate_values = second_backorder.move_line_ids._get_aggregated_product_quantities()
        self.assertEqual(len(aggregate_values), 2)
        sml1 = second_backorder.move_line_ids.filtered(lambda ml: ml.product_id == product3)
        sm2 = second_backorder.move_lines.filtered(lambda ml: ml.product_id == product2)
        aggregate_val_1 = aggregate_values[f'{product3.id}_{product3.name}__{sml1.product_uom_id.id}']
        aggregate_val_2 = aggregate_values[f'{product2.id}_{product2.name}__{sm2.product_uom.id}']
        self.assertEqual(aggregate_val_1['qty_ordered'], 3)
        self.assertEqual(aggregate_val_1['qty_done'], 3)
        self.assertEqual(aggregate_val_2['qty_ordered'], 2)
        self.assertEqual(aggregate_val_2['qty_done'], 0)

    def test_move_line_aggregated_product_quantities_duplicate_stock_move(self):
        """ Test the `stock.move.line` method `_get_aggregated_product_quantities`,
        which returns data used to print delivery slips, with two stock moves of the same product
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 25)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'picking_id': picking.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_transit_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
            'picking_id': picking.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'qty_done': 10,
            'product_uom_id': move1.product_uom.id,
            'picking_id': picking.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
        })
        self.env['stock.move.line'].create({
            'move_id': move2.id,
            'product_id': move2.product_id.id,
            'qty_done': 5,
            'product_uom_id': move2.product_uom.id,
            'picking_id': picking.id,
            'location_id': move2.location_id.id,
            'location_dest_id': move2.location_dest_id.id,
        })
        aggregate_values = picking.move_line_ids._get_aggregated_product_quantities()
        aggregated_val = aggregate_values[f'{self.product.id}_{self.product.name}__{self.product.uom_id.id}']
        self.assertEqual(aggregated_val['qty_ordered'], 15)
        picking.button_validate()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 10)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.customer_location), 15)

    def test_move_line_aggregated_product_quantities_two_packages(self):
        """ Test the `stock.move.line` method `_get_aggregated_product_quantities`,
        which returns data used to print delivery slips, with two packages
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 25)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
            'picking_id': picking.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        picking.action_confirm()
        picking.action_assign()
        move1.quantity_done = 5
        picking.action_put_in_pack()  # Create a first package
        self.assertEqual(len(picking.move_line_ids), 2)

        unpacked_ml = picking.move_line_ids.filtered(lambda ml: not ml.result_package_id)
        self.assertEqual(unpacked_ml.product_qty, 10)
        unpacked_ml.qty_done = 10
        picking.action_put_in_pack()  # Create a second package
        self.assertEqual(len(picking.move_line_ids), 2)

        picking.button_validate()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 10)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.customer_location), 15)

        aggregate_values1 = picking.move_line_ids[0]._get_aggregated_product_quantities(strict=True)
        aggregated_val = aggregate_values1[f'{self.product.id}_{self.product.name}__{self.product.uom_id.id}']
        self.assertEqual(aggregated_val['qty_ordered'], 10)

        aggregate_values2 = picking.move_line_ids[1]._get_aggregated_product_quantities(strict=True)
        aggregated_val = aggregate_values2[f'{self.product.id}_{self.product.name}__{self.product.uom_id.id}']
        self.assertEqual(aggregated_val['qty_ordered'], 5)

    def test_move_line_aggregated_product_quantities_incomplete_package(self):
        """ Test the `stock.move.line` method `_get_aggregated_product_quantities`,
        which returns data used to print delivery slips, with an incomplete order put in packages
        """
        self.env['stock.quant']._update_available_quantity(self.product, self.stock_location, 25)
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1 = self.env['stock.move'].create({
            'name': 'test_transit_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
            'picking_id': picking.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move1.quantity_done = 5
        picking.action_put_in_pack()  # Create a package

        delivery_form = Form(picking)
        delivery = delivery_form.save()
        delivery.action_confirm()

        backorder_wizard_dict = delivery.button_validate()
        backorder_wizard_form = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context']))
        backorder_wizard_form.save().process_cancel_backorder()  # Don't create a backorder

        aggregate_values = picking.move_line_ids._get_aggregated_product_quantities()
        aggregated_val = aggregate_values[f'{self.product.id}_{self.product.name}__{self.product.uom_id.id}']
        self.assertEqual(aggregated_val['qty_ordered'], 15)
        self.assertEqual(aggregated_val['qty_done'], 5)

        aggregate_values = picking.move_line_ids._get_aggregated_product_quantities(strict=True)
        aggregated_val = aggregate_values[f'{self.product.id}_{self.product.name}__{self.product.uom_id.id}']
        self.assertEqual(aggregated_val['qty_ordered'], 5)
        self.assertEqual(aggregated_val['qty_done'], 5)

        aggregate_values = picking.move_line_ids._get_aggregated_product_quantities(except_package=True)
        aggregated_val = aggregate_values[f'{self.product.id}_{self.product.name}__{self.product.uom_id.id}']
        self.assertEqual(aggregated_val['qty_ordered'], 10)
        self.assertEqual(aggregated_val['qty_done'], False)

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.stock_location), 20)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product, self.customer_location), 5)

    def test_move_sn_warning(self):
        """ Check that warnings pop up when duplicate SNs added or when SN isn't in
        expected location.
        Two cases covered:
        - Check for dupes when assigning serial number to a stock move
        - Check for dupes when assigning serial number to a stock move line
        """

        lot1 = self.env['stock.production.lot'].create({
            'name': 'serial1',
            'product_id': self.product_serial.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(self.product_serial, self.pack_location, 1, lot1)

        move = self.env['stock.move'].create({
            'name': 'test sn',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product_serial.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })

        move_line = self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': move.product_id.id,
            'qty_done': 1,
            'product_uom_id': move.product_uom.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'lot_name': lot1.name,
        })

        warning = False
        warning = move_line._onchange_serial_number()
        self.assertTrue(warning, 'Reuse of existing serial number (name) not detected')
        self.assertEqual(list(warning.keys())[0], 'warning', 'Warning message was not returned')

        move_line.write({
            'lot_name': False,
            'lot_id': lot1.id
        })

        warning = False
        warning = move_line._onchange_serial_number()
        self.assertTrue(warning, 'Reuse of existing serial number (record) not detected')
        self.assertEqual(list(warning.keys())[0], 'warning', 'Warning message was not returned')
        self.assertEqual(move_line.location_id, self.pack_location, 'Location was not auto-corrected')

        move.lot_ids = lot1
        warning = False
        warning = move._onchange_lot_ids()
        self.assertTrue(warning, 'Reuse of existing serial number (record) not detected')
        self.assertEqual(list(warning.keys())[0], 'warning', 'Warning message was not returned')

    def test_forecast_availability(self):
        """ Make an outgoing picking in dozens for a product stored in units.
        Check that reserved_availabity is expressed in move uom and forecast_availability is in product base uom
        """
        # create product
        product = self.env['product.product'].create({
            'name': 'Product In Units',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        # make some stock
        self.env['stock.quant']._update_available_quantity(product, self.stock_location, 36.0)
        # create picking
        picking_out = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id})
        move = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 2.0,
            'picking_id': picking_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id})
        # confirm
        picking_out.action_confirm()
        # check availability
        picking_out.action_assign()
        # check reserved_availabity expressed in move uom
        self.assertEqual(move.reserved_availability, 2)
        # check forecast_availability expressed in product base uom
        self.assertEqual(move.forecast_availability, 24)

    def test_SML_location_selection(self):
        """
        Suppose the setting 'Storage Categories' disabled and the option 'Show Detailed Operations'
        for operation 'Internal Transfer' enabled.
        A user creates an internal transfer from F to T, confirms it then adds a SML and selects
        another destination location L (with L a child of T). When the user completes the field
        `qty_done`, the onchange should n't change the destination location L
        """

        self.env.user.write({'groups_id': [(3, self.env.ref('stock.group_stock_storage_categories').id)]})
        internal_transfer = self.env.ref('stock.picking_type_internal')
        internal_transfer.show_operations = True

        picking = self.env['stock.picking'].create({
            'picking_type_id': internal_transfer.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        self.env['stock.move'].create({
            'name': self.product_consu.name,
            'product_id': self.product_consu.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
        })

        picking.action_confirm()

        with Form(picking) as form:
            with form.move_line_ids_without_package.edit(0) as line:
                line.location_dest_id = self.stock_location.child_ids[0]
                line.qty_done = 1

        self.assertEqual(picking.move_line_ids_without_package.location_dest_id, self.stock_location.child_ids[0])

    def test_inter_wh_and_forecast_availability(self):
        dest_wh = self.env['stock.warehouse'].create({
            'name': 'Second Warehouse',
            'code': 'WH02',
        })

        move = self.env['stock.move'].create({
            'name': 'test_interwh',
            'location_id': self.stock_location.id,
            'location_dest_id': dest_wh.lot_stock_id.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        self.assertEqual(move.forecast_availability, -1)
        move._action_confirm()
        self.assertEqual(move.forecast_availability, -1)

    def test_receive_more_and_in_child_location(self):
        """
        Ensure that, when receiving more than expected, and when the destination
        location of the SML is different from the SM one, the SM validation will
        not change the destination location of the SML
        """
        move = self.env['stock.move'].create({
            'name': self.product.name,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move._action_confirm()
        move.move_line_ids.write({
            'location_dest_id': self.stock_location.child_ids[0].id,
            'qty_done': 3,
        })
        move._action_done()
        self.assertEqual(move.move_line_ids.qty_done, 3)
        self.assertEqual(move.move_line_ids.location_dest_id, self.stock_location.child_ids[0])
