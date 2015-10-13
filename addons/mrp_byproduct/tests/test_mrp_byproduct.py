# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.tests import common


class TestMrpByProduct(common.TransactionCase):

    def setUp(self):
        super(TestMrpByProduct, self).setUp()
        self.MrpProduction = self.env['mrp.production']
        self.MrpBom = self.env['mrp.bom']
        self.Move = self.env['stock.move']
        self.MrpProductProduce = self.env['mrp.product.produce']
        self.product_28 = self.env.ref('product.product_product_28')
        self.product_33_id = self.ref('product.product_product_33')
        self.product_uom_id = self.ref('product.product_uom_unit')
        self.location_src_id = self.ref('stock.stock_location_stock')
        self.mrp_action_id = self.ref('mrp.menu_mrp_production_action')

    def test_00_mrp_byproduct(self):
        # I add a sub product in Bill of material for product External Hard Disk.
        bom_hardisk = self.MrpBom.create({'product_tmpl_id': self.product_28.product_tmpl_id.id,
                                          'product_uom': self.product_uom_id,
                                          'sub_products_ids': [(0, 0, {'product_id': self.product_33_id,
                                                                       'product_uom_id': self.product_uom_id,
                                                                       'product_qty': 2.0,
                                                                       'subproduct_type': 'fixed'})]})
        # I create a production order for External Hard Disk
        mnf_hardisk = self.MrpProduction.create({'product_id': self.product_28.id,
                                                 'product_qty': 2.0,
                                                 'product_uom': self.product_uom_id,
                                                 'bom_id': bom_hardisk.id,
                                                 'location_src_id': self.location_src_id})

        # I compute the data of production order
        context = {"active_ids": [mnf_hardisk.id], "active_id": mnf_hardisk.id}
        mnf_hardisk.with_context(context).action_compute()

        # I confirm the production order.
        mnf_hardisk.signal_workflow('button_confirm')

        # I confirm the production order.
        self.assertEqual(mnf_hardisk.state, 'confirmed', 'Production order should be in state confirmed')

        #Now I check the stock moves for the byproduct I created in the bill of material.
        #This move is created automatically when I confirmed the production order.
        moves = self.Move.search([('product_id', '=', self.product_33_id)])
        self.assertTrue(moves, 'No moves are created !')

        #I want to start the production so I force the reservation of products.
        context = {"active_ids": [self.mrp_action_id], "active_id": self.mrp_action_id}
        mnf_hardisk.with_context(context).force_production()

        #I start the production.
        mnf_hardisk.signal_workflow('button_produce')

        #I consume and produce the production of products.
        #I create record for selecting mode and quantity of products to produce.
        product_consume = self.MrpProductProduce.create({'product_qty': 2.00,
                                                         'mode': 'consume_produce'
                                                         })
        #I finish the production order.
        context = {"active_model": "mrp.production", "active_ids": [mnf_hardisk.id], "active_id": mnf_hardisk.id}
        qty = product_consume.product_qty
        lines = product_consume.with_context(context).on_change_qty(qty, [])
        product_consume.write(lines['value'])
        product_consume.with_context(context).do_produce()

        #I see that stock moves of External Hard Disk including Headset USB are done now.
        moves = self.Move.search([('origin', '=', mnf_hardisk.name), ('product_id', 'in', [self.product_28.id, self.product_33_id])])
        for move in moves:
            self.assertEqual(move.state, 'done', 'Moves are not done!')
