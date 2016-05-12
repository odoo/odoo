# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


class TestMrpByProduct(common.TransactionCase):

    def setUp(self):
        super(TestMrpByProduct, self).setUp()
        self.product_28 = self.env.ref('product.product_delivery_02')
        self.product_33 = self.env.ref('product.product_delivery_01')
        self.product_uom = self.env.ref('product.product_uom_unit')
        self.location_src = self.env.ref('stock.stock_location_stock')
        self.mrp_action = self.env.ref('mrp.menu_mrp_production_action')

    def test_00_mrp_byproduct(self):
        # I add a sub product in Bill of material for product External Hard Disk.
        bom_hardisk = self.env['mrp.bom'].create({'product_tmpl_id': self.product_28.product_tmpl_id.id,
                                          'product_uom': self.product_uom.id,
                                          'sub_products': [(0, 0, {'product_id': self.product_33.id,
                                                                     'product_uom': self.product_uom.id,
                                                                     'product_qty': 2.0,
                                                                     'subproduct_type': 'fixed'})]})
        # I create a production order for External Hard Disk
        mnf_hardisk = self.env['mrp.production'].create({'product_id': self.product_28.id,
                                                 'product_qty': 2.0,
                                                 'product_uom': self.product_uom.id,
                                                 'bom_id': bom_hardisk.id,
                                                 'location_src_id': self.location_src.id})

        # I compute the data of production order
        context = {"active_ids": [mnf_hardisk.id], "active_id": mnf_hardisk.id}
        mnf_hardisk.with_context(context).action_compute()

        # I confirm the production order.
        mnf_hardisk.signal_workflow('button_confirm')

        # I confirm the production order.
        self.assertEqual(mnf_hardisk.state, 'confirmed', 'Production order should be in state confirmed')

        # Now I check the stock moves for the byproduct I created in the bill of material.
        # This move is created automatically when I confirmed the production order.
        moves = self.env['stock.move'].search([('product_id', '=', self.product_33.id)])
        self.assertTrue(moves, 'No moves are created !')

        # I want to start the production so I force the reservation of products.
        context = {"active_ids": [self.mrp_action.id], "active_id": self.mrp_action.id}
        mnf_hardisk.with_context(context).force_production()

        # I start the production.
        mnf_hardisk.signal_workflow('button_produce')

        # I consume and produce the production of products.
        # I create record for selecting mode and quantity of products to produce.
        product_consume = self.env['mrp.product.produce'].create({'product_qty': 2.00,
                                                         'mode': 'consume_produce'
                                                         })
        # I finish the production order.
        context = {"active_model": "mrp.production", "active_ids": [mnf_hardisk.id], "active_id": mnf_hardisk.id}
        product_consume.with_context(context).on_change_qty()
        product_consume.with_context(context).do_produce()

        # I see that stock moves of External Hard Disk including Headset USB are done now.
        moves = self.env['stock.move'].search([('origin', '=', mnf_hardisk.name), ('product_id', 'in', [self.product_28.id, self.product_33.id])])
        self.assertTrue(bool(moves))
        for move in moves:
            self.assertEqual(move.state, 'done', 'Moves are not done!')