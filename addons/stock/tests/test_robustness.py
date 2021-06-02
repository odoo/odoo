# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import SavepointCase


class TestRobustness(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestRobustness, cls).setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        cls.product1 = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
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
            'name': 'test_uom_rounding',
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
        self.assertEqual(move1.product_qty, 12)

        # change the factor
        with self.assertRaises(UserError):
            with self.cr.savepoint():
                move1.product_uom.factor = 0.05

        # assert the reservation
        self.assertEqual(quant.reserved_quantity, 12)
        self.assertEqual(move1.state, 'assigned')
        self.assertEqual(move1.product_qty, 12)

        # unreserve
        move1._do_unreserve()

    def test_location_usage(self):
        """ Changing the usage of a location shouldn't be allowed while
        quantities are reserved, else the existing move lines won't be
        consistent with the `reserved_quantity` on the quants.
        """
        # change stock usage
        test_stock_location = self.env['stock.location'].create({
            'name': "Test Location",
            'location_id': self.stock_location.id,
        })
        test_stock_location.scrap_location = True

        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.product1,
            test_stock_location,
            1,
        )

        # reserve a unit
        move1 = self.env['stock.move'].create({
            'name': 'test_location_archive',
            'location_id': test_stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
        })
        move1._action_confirm()
        move1._action_assign()
        self.assertEqual(move1.state, 'assigned')
        quant = self.env['stock.quant']._gather(
            self.product1,
            test_stock_location,
        )

        # assert the reservation
        self.assertEqual(quant.reserved_quantity, 0)  # reservation is bypassed in scrap location
        self.assertEqual(move1.product_qty, 1)

        # change the stock usage
        with self.assertRaises(UserError):
            with self.cr.savepoint():
                test_stock_location.scrap_location = False

        # unreserve
        move1._do_unreserve()

    def test_package_unpack(self):
        """ Unpack a package that contains quants with a reservation
        should also remove the package on the reserved move lines.
        """
        package = self.env['stock.quant.package'].create({
            'name': 'Shell Helix HX7 10W30',
        })

        self.env['stock.quant']._update_available_quantity(
            self.product1,
            self.stock_location,
            10,
            package_id=package
        )

        # reserve a dozen
        move1 = self.env['stock.move'].create({
            'name': 'test_uom_rounding',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
        })
        move1._action_confirm()
        move1._action_assign()

        move1.result_package_id = False

        package.unpack()

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
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'tracking': 'lot',
        })
        product2 = self.env['product.product'].create({
            'name': 'Product 2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'tracking': 'lot',
        })

        lot1 = self.env['stock.production.lot'].create({
            'name': 'lot1',
            'product_id': product1.id,
            'company_id': self.env.company.id,

        })
        lot2 = self.env['stock.production.lot'].create({
            'name': 'lot2',
            'product_id': product2.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant']._update_available_quantity(product1, self.stock_location, 1, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(product2, self.stock_location, 1, lot_id=lot2)

        move1 = self.env['stock.move'].create({
            'name': 'test_lot_id_product_id_mix_move_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_lot_id_product_id_mix_move_2',
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
                'qty_done': 1,
                'lot_id': lot2.id,
                'location_id': move1.location_id.id,
                'location_dest_id': move1.location_dest_id.id,
            })]})

        with self.assertRaises(ValidationError):
            move2.write({'move_line_ids': [(0, 0, {
                'product_id': product2.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 1,
                'lot_id': lot1.id,
                'location_id': move2.location_id.id,
                'location_dest_id': move2.location_dest_id.id,
            })]})

