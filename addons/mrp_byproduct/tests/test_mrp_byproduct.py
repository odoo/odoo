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
        self.product_33 = self.env.ref('product.product_product_33')
        self.product_uom = self.env.ref('product.product_uom_unit')
        self.location_src = self.env.ref('stock.stock_location_stock')
        self.mrp_action = self.env.ref('mrp.menu_mrp_production_action')

    def test_00_mrp_byproduct(self):
        # I add a sub product in Bill of material for product External Hard Disk.
        bom_hardisk = self.MrpBom.create({'product_tmpl_id': self.product_28.product_tmpl_id.id,
                                          'product_uom_id': self.product_uom.id,
                                          'subproduct_ids': [(0, 0, {'product_id': self.product_33.id,
                                                                     'product_uom_id': self.product_uom.id,
                                                                     'product_qty': 2.0,
                                                                     'subproduct_type': 'fixed'})]})
        # I create a production order for External Hard Disk
        mnf_hardisk = self.MrpProduction.create({'product_id': self.product_28.id,
                                                 'product_qty': 2.0,
                                                 'product_uom_id': self.product_uom.id,
                                                 'bom_id': bom_hardisk.id,
                                                 'location_src_id': self.location_src.id})

        # I compute the data of production order
        context = {"active_ids": [mnf_hardisk.id], "active_id": mnf_hardisk.id}

        # I confirm the production order
        self.assertEqual(mnf_hardisk.state, 'confirmed', 'Production order should be in state confirmed')

        # Now I check the stock moves for the byproduct I created in the bill of material.
        # This move is created automatically when I confirmed the production order.
        moves = self.Move.search([('product_id', '=', self.product_33.id)])
        self.assertTrue(moves, 'No moves are created !')

        # I consume and produce the production of products.
        # I create record for selecting mode and quantity of products to produce.
        product_consume = self.MrpProductProduce.create({'product_qty': 2.00})
        # I finish the production order.
        context = {"active_model": "mrp.production", "active_ids": [mnf_hardisk.id], "active_id": mnf_hardisk.id}
        product_consume.with_context(context).do_produce()
        
        mnf_hardisk.post_inventory()

        # I see that stock moves of External Hard Disk including Headset USB are done now.
        moves = self.Move.search([('origin', '=', mnf_hardisk.name), ('product_id', 'in', [self.product_28.id, self.product_33.id])])
        for move in moves:
            self.assertEqual(move.state, 'done', 'Moves are not done!')
        
        