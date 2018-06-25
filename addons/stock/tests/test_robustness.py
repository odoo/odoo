# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestRobustness(TransactionCase):
    def setUp(self):
        super(TestRobustness, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.uom_unit = self.env.ref('product.product_uom_unit')
        self.uom_dozen = self.env.ref('product.product_uom_dozen')
        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
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
        self.stock_location.scrap_location = True

        # make some stock
        self.env['stock.quant']._update_available_quantity(
            self.product1,
            self.stock_location,
            1,
        )

        # reserve a unit
        move1 = self.env['stock.move'].create({
            'name': 'test_location_archive',
            'location_id': self.stock_location.id,
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
            self.stock_location,
        )

        # assert the reservation
        self.assertEqual(quant.reserved_quantity, 0)  # reservation is bypassed in scrap location
        self.assertEqual(move1.product_qty, 1)

        # change the stock usage
        with self.assertRaises(UserError):
            with self.cr.savepoint():
                self.stock_location.scrap_location = False

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
