# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Leonardo Pistone
# Copyright 2015 Camptocamp SA

from odoo.addons.stock.tests.common2 import TestStockCommon


class TestVirtualAvailable(TestStockCommon):

    def setUp(self):
        super(TestVirtualAvailable, self).setUp()

        self.env['stock.quant'].create({
            'product_id': self.product_3.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'qty': 30.0})

        self.env['stock.quant'].create({
            'product_id': self.product_3.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'qty': 10.0,
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
