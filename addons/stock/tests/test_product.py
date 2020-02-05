# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Leonardo Pistone
# Copyright 2015 Camptocamp SA

from odoo.addons.stock.tests.common2 import TestStockCommon
from odoo.tests.common import Form


class TestVirtualAvailable(TestStockCommon):
    def setUp(self):
        super(TestVirtualAvailable, self).setUp()

        # Make `product3` a storable product for this test. Indeed, creating quants
        # and playing with owners is not possible for consumables.
        self.product_3.type = 'product'

        self.env['stock.quant'].create({
            'product_id': self.product_3.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 30.0})

        self.env['stock.quant'].create({
            'product_id': self.product_3.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 10.0,
            'owner_id': self.user_stock_user.partner_id.id})

        self.picking_out = self.env['stock.picking'].create({
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id})
        self.env['stock.move'].create({
            'name': 'a move',
            'product_id': self.product_3.id,
            'product_uom_qty': 3.0,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_out.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id})

        self.picking_out_2 = self.env['stock.picking'].create({
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id})
        self.env['stock.move'].create({
            'restrict_partner_id': self.user_stock_user.partner_id.id,
            'name': 'another move',
            'product_id': self.product_3.id,
            'product_uom_qty': 5.0,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_out_2.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id})

    def test_without_owner(self):
        self.assertAlmostEqual(40.0, self.product_3.virtual_available)
        self.picking_out.action_assign()
        self.picking_out_2.action_assign()
        self.assertAlmostEqual(32.0, self.product_3.virtual_available)

    def test_with_owner(self):
        prod_context = self.product_3.with_context(owner_id=self.user_stock_user.partner_id.id)
        self.assertAlmostEqual(10.0, prod_context.virtual_available)
        self.picking_out.action_assign()
        self.picking_out_2.action_assign()
        self.assertAlmostEqual(5.0, prod_context.virtual_available)

    def test_free_quantity(self):
        """ Test the value of product.free_qty. Free_qty = qty_on_hand - qty_reserved"""
        self.assertAlmostEqual(40.0, self.product_3.free_qty)
        self.picking_out.action_confirm()
        self.picking_out_2.action_confirm()
        # No reservation so free_qty is unchanged
        self.assertAlmostEqual(40.0, self.product_3.free_qty)
        self.picking_out.action_assign()
        self.picking_out_2.action_assign()
        # 8 units are now reserved
        self.assertAlmostEqual(32.0, self.product_3.free_qty)
        self.picking_out.do_unreserve()
        self.picking_out_2.do_unreserve()
        # 8 units are available again
        self.assertAlmostEqual(40.0, self.product_3.free_qty)

    def test_archive_product_1(self):
        """`qty_available` and `virtual_available` are computed on archived products"""
        self.assertTrue(self.product_3.active)
        self.assertAlmostEqual(40.0, self.product_3.qty_available)
        self.assertAlmostEqual(40.0, self.product_3.virtual_available)
        self.product_3.active = False
        self.assertAlmostEqual(40.0, self.product_3.qty_available)
        self.assertAlmostEqual(40.0, self.product_3.virtual_available)

    def test_archive_product_2(self):
        """Archiving a product should archive its reordering rules"""
        self.assertTrue(self.product_3.active)
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = self.product_3
        orderpoint_form.location_id = self.env.ref('stock.stock_location_stock')
        orderpoint_form.product_min_qty = 0.0
        orderpoint_form.product_max_qty = 5.0
        orderpoint = orderpoint_form.save()
        self.assertTrue(orderpoint.active)
        self.product_3.active = False
        self.assertFalse(orderpoint.active)
