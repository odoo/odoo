# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestRobustness(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestRobustness, cls).setUpClass()
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        cls.product1 = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
        })

    def test_uom_factor(self):
        """ Changing the factor of a unit of measure shouldn't be allowed while
        quantities are reserved, else the existing move lines won't be consistent
        with the `reserved_quantity` on quants.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.product1,
            self.stock_location,
            12,
        )

        # reserve a dozen
        move1 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_dozen.id,
            'product_uom_qty': 1,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        quant = self.env['stock.quant']._gather(
            self.product1,
            self.stock_location,
        )

        # assert the reservation
        self.assertEqual(quant.reserved_quantity, 12)
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move1.product_qty, 12)

        # unreserve
        move1._do_unreserve()

    def test_location_usage(self):
        """Changing the usage of a location shouldn't be allowed
        or changing a location from scrap to non-scrap or vice versa
        shouldn't be allowed when stock is available in a location"""
        # change stock usage
        test_stock_location = self.env['stock.location'].create({
            'name': "Test Location",
            'location_id': self.stock_location.id,
        })
        test_stock_location.usage = 'inventory'

        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.product1,
            test_stock_location,
            1,
        )

        # reserve a unit
        move = self.env['stock.move'].create({
            'location_id': test_stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
        })
        move._action_confirm()
        move._action_assign()
        move.picked = True
        move._action_done()
        self.assertEqual(move.state, 'done')

        # change the stock usage
        test_stock_location.usage = 'internal'

        # make some stock again
        self.env['stock.quant']._update_available_quantity(
            self.product1,
            test_stock_location,
            1,
        )

        # change the stock usage again
        with self.assertRaises(UserError):
            test_stock_location.usage = 'inventory'

    def test_package_unpack(self):
        """ Unpack a package that contains quants with a reservation
        should also remove the package on the reserved move lines.
        """
        package = self.env['stock.package'].create({
            'name': 'Shell Helix HX7 10W30',
        })

        self.env['stock.quant']._update_available_quantity(
            self.product1,
            self.stock_location,
            10,
            package_id=package
        )

        # reserve 10 units
        move1 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
        })
        move1._action_confirm()
        move1._action_assign()

        self.assertEqual(move1.move_line_ids.package_id, package)
        package.unpack()
        self.assertEqual(move1.move_line_ids.package_id, self.env['stock.package'])

        # unreserve
        move1._do_unreserve()
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location, package_id=package)), 0)

        self.assertEqual(self.env['stock.quant']._gather(self.product1, self.stock_location).reserved_quantity, 0)

    def test_lot_id_product_id_mix(self):
        """ Make sure it isn't possible to create a move line with a lot incompatible with its
        product.
        """
        product1 = self.env['product.product'].create({
            'name': 'Product 1',
            'is_storable': True,
            'tracking': 'lot',
        })
        product2 = self.env['product.product'].create({
            'name': 'Product 2',
            'is_storable': True,
            'tracking': 'lot',
        })

        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': product1.id,

        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': product2.id,
        })

        self.env['stock.quant']._update_available_quantity(product1, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(product2, self.stock_location, 1, lot_id=lot2)

        move1 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        (move1 + move2)._action_confirm()

        with self.assertRaises(ValidationError):
            move1.write({'move_line_ids': [(0, 0, {
                'product_id': product1.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 1,
                'lot_id': lot2.id,
                'location_id': move1.location_id.id,
                'location_dest_id': move1.location_dest_id.id,
            })]})

        with self.assertRaises(ValidationError):
            move2.write({'move_line_ids': [(0, 0, {
                'product_id': product2.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 1,
                'lot_id': lot1.id,
                'location_id': move2.location_id.id,
                'location_dest_id': move2.location_dest_id.id,
            })]})

    def test_lot_quantity_remains_unchanged_after_done(self):
        """ Make sure the method _set_lot_ids does not change the quantities of lots to 1 once they are done.
        """
        productA = self.env['product.product'].create({
            'name': 'ProductA',
            'is_storable': True,
            'tracking': 'lot',
        })
        lotA = self.env['stock.lot'].create({
            'name': 'lotA',
            'product_id': productA.id,

        })
        self.env['stock.quant']._update_available_quantity(productA, self.stock_location, 5, lot_id=lotA)
        moveA = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': productA.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })

        moveA._action_confirm()
        moveA.write({'move_line_ids': [(0, 0, {
            'product_id': productA.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 5,
            'lot_id': lotA.id,
            'location_id': moveA.location_id.id,
            'location_dest_id': moveA.location_dest_id.id,
        })]})
        moveA._action_done()
        moveA._set_lot_ids()

        self.assertEqual(moveA.quantity, 5)

    def test_new_move_done_picking(self):
        """ Ensure that adding a Draft move to a Done picking doesn't change the picking state
        """
        product1 = self.env['product.product'].create({'name': 'P1', 'is_storable': True})
        product2 = self.env['product.product'].create({'name': 'P2', 'is_storable': True})

        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1 = self.env['stock.move'].create({
            'location_id': receipt.location_id.id,
            'location_dest_id': receipt.location_dest_id.id,
            'picking_id': receipt.id,
            'product_id': product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        receipt.action_confirm()
        receipt.action_assign()
        move1.picked = True
        # move1.move_line_ids.quantity = 1

        receipt.button_validate()

        self.assertEqual(receipt.state, 'done')
        self.assertEqual(move1.state, 'done')

        move2 = self.env['stock.move'].create({
            'location_id': receipt.location_id.id,
            'location_dest_id': receipt.location_dest_id.id,
            'picking_id': receipt.id,
            'state': 'draft',
            'product_id': product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'quantity': 1.0,
        })

        self.assertEqual(receipt.state, 'done')
        self.assertEqual(move1.state, 'done')
        self.assertEqual(move2.state, 'done')

    def test_clean_quants_synch(self):
        """ Ensure the _clean_reservaion method align the quants on stock.move.line """
        product_reservation_too_high = self.env['product.product'].create({
            'name': 'Product Reservation',
            'is_storable': True,
        })
        self.env['stock.quant']._update_available_quantity(product_reservation_too_high, self.stock_location, 10)
        quant = self.env['stock.quant']._gather(product_reservation_too_high, self.stock_location)

        move = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': product_reservation_too_high.id,
            'product_uom_qty': 5,
        })
        move._action_confirm()
        move._action_assign()

        self.env['stock.quant']._update_reserved_quantity(product_reservation_too_high, self.stock_location, 2)
        self.assertEqual(quant.reserved_quantity, 7)
        self.env['stock.quant']._clean_reservations()
        self.assertEqual(quant.reserved_quantity, 5)

        self.env['stock.quant']._update_reserved_quantity(product_reservation_too_high, self.stock_location, -2)
        self.assertEqual(quant.reserved_quantity, 3)
        self.env['stock.quant']._clean_reservations()
        self.assertEqual(quant.reserved_quantity, 5)

        self.env['stock.quant']._update_reserved_quantity(product_reservation_too_high, self.stock_location, -2)
        self.assertEqual(quant.reserved_quantity, 3)
        move.picked = True
        move._action_done()
        self.assertEqual(quant.reserved_quantity, 0)

        product_without_move = self.env['product.product'].create({
            'name': 'Product reserved without move',
            'is_storable': True,
        })
        self.env['stock.quant']._update_available_quantity(product_without_move, self.stock_location, 10)
        quant = self.env['stock.quant']._gather(product_without_move, self.stock_location)
        self.env['stock.quant']._update_reserved_quantity(product_without_move, self.stock_location, 2)

        self.assertEqual(quant.reserved_quantity, 2)
        self.env['stock.quant']._clean_reservations()
        self.assertEqual(quant.reserved_quantity, 0)

    def test_clean_quants_synch_with_different_uom(self):
        """ Ensure the _clean_reservaion method align the quants on stock.move.line when using different UoM """
        uom_kg = self.env.ref('uom.product_uom_kgm')
        product_reservation_too_high = self.env['product.product'].create({
            'name': 'Product Reservation',
            'is_storable': True,
            'uom_id': uom_kg.id,
        })
        # update available quantity to 1 kg
        self.env['stock.quant']._update_available_quantity(product_reservation_too_high, self.stock_location, 1)
        quant = self.env['stock.quant']._gather(product_reservation_too_high, self.stock_location)
        # reserve 0.1 kg with a move
        move = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': product_reservation_too_high.id,
            'product_uom_qty': 100,
            'product_uom': self.env.ref('uom.product_uom_gram').id,
        })
        move._action_confirm()
        move._action_assign()
        # update reserved quantity to 0.2 kg
        self.env['stock.quant']._update_reserved_quantity(product_reservation_too_high, self.stock_location, 0.2)
        self.assertEqual(quant.reserved_quantity, 0.3)
        self.env['stock.quant']._clean_reservations()
        # the reserved quantity should be cleaned to the quantity reserved by the move
        self.assertEqual(quant.reserved_quantity, 0.1)

    def test_clean_quants_synch_in_non_company_specific_locations(self):
        """
        Accessing the inventory view will add an inventory_mode in the context
        and launch a call of the `_clean_reservation`.

        This checks that the _clean_reservation method does not raise user errors if it
        plans to create a quants in a non-company specific location.
        """
        product_without_quant = self.env['product.product'].create({
            'name': 'Product reserved without quant',
            'is_storable': True,
            'company_id': self.stock_location.company_id.id,
        })
        reservation_move = self.env['stock.move'].create({
            'company_id': self.stock_location.company_id.id,
            'location_id': self.ref('stock.stock_location_inter_company'),
            'location_dest_id': self.stock_location.id,
            'product_id': product_without_quant.id,
            'product_uom': product_without_quant.uom_id.id,
            'product_uom_qty': 5.0,
        })

        reservation_move._action_confirm()
        reservation_move.quantity = 5
        self.assertRecordValues(product_without_quant.stock_quant_ids, [
            {'location_id': self.ref('stock.stock_location_inter_company'), 'reserved_quantity': 5.0}
        ])
        # create a syncj issue
        product_without_quant.stock_quant_ids.unlink()
        self.assertFalse(product_without_quant.stock_quant_ids)
        # acces the quant view to provoke a quant synch
        self.env['stock.quant'].action_view_quants()
        self.assertRecordValues(product_without_quant.stock_quant_ids, [
            {'location_id': self.ref('stock.stock_location_inter_company'), 'reserved_quantity': 5.0}
        ])
