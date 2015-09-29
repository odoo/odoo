# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Leonardo Pistone
# Copyright 2015 Camptocamp SA

from openerp.addons.stock.tests.common import TestStockCommon


class TestVirtualAvailable(TestStockCommon):

    def setUp(self):
        super(TestVirtualAvailable, self).setUp()

        self.env['stock.quant'].create({
            'product_id': self.productA.id,
            'location_id': self.stock_location,
            'qty': 30.0,
        })

        self.env['stock.quant'].create({
            'product_id': self.productA.id,
            'location_id': self.stock_location,
            'qty': 10.0,
            'owner_id': self.ref('base.res_partner_4'),
        })

        self.picking_out = self.env['stock.picking'].create({
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.env['stock.move'].create({
            'name': 'a move',
            'product_id': self.productA.id,
            'product_uom_qty': 3.0,
            'product_uom': self.productA.uom_id.id,
            'picking_id': self.picking_out.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location
            })

        self.picking_out_2 = self.env['stock.picking'].create({
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location})
        self.env['stock.move'].create({
            'restrict_partner_id': self.ref('base.res_partner_4'),
            'name': 'another move',
            'product_id': self.productA.id,
            'product_uom_qty': 5.0,
            'product_uom': self.productA.uom_id.id,
            'picking_id': self.picking_out_2.id,
            'location_id': self.stock_location,
            'location_dest_id': self.customer_location
            })


    def test_without_owner(self):
        self.assertAlmostEqual(40.0, self.productA.virtual_available)
        self.picking_out.action_assign()
        self.picking_out_2.action_assign()

        self.assertAlmostEqual(32.0, self.productA.virtual_available)

    def test_with_owner(self):
        prod_context = self.productA.with_context(
            owner_id=self.ref('base.res_partner_4')
        )
        self.assertAlmostEqual(10.0, prod_context.virtual_available)
        self.picking_out.action_assign()
        self.picking_out_2.action_assign()
        self.assertAlmostEqual(5.0, prod_context.virtual_available)
