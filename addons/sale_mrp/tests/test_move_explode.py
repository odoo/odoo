# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestMoveExplode(common.TransactionCase):

    def setUp(self):
        super(TestMoveExplode, self).setUp()
        # Usefull models
        self.SaleOrderLine = self.env['sale.order.line']
        self.SaleOrder = self.env['sale.order']
        self.MrpBom = self.env['mrp.bom']
        self.Product = self.env['product.product']

        #product that has a phantom bom
        self.product_bom = self.env.ref('product.product_product_5')
        #bom with that product
        self.bom = self.env.ref('mrp.mrp_bom_kit')
        #partner agrolait
        self.partner = self.env.ref('base.res_partner_1')
        #bom: PC Assemble (with property: DDR 512MB)
#         self.bom_prop = self.env.ref('mrp.mrp_bom_property_0')
        self.template = self.env.ref('product.product_product_3_product_template')
        #product: RAM SR2
        self.product_bom_prop = self.env.ref('product.product_product_5')
        #phantom bom for RAM SR2 with three lines containing properties
#         self.bom_prop_line = self.env.ref('mrp.mrp_bom_property_line')
        #product: iPod included in the phantom bom
        self.product_A = self.env.ref('product.product_product_11')
        #product: Mouse, Wireless included in the phantom bom
        self.product_B = self.env.ref('product.product_product_12')
        #pricelist
        self.pricelist = self.env.ref('product.list0')


    def test_00_sale_move_explode(self):
        """check that when creating a sale order with a product that has a phantom BoM, move explode into content of the
            BoM"""
        #create sale order with one sale order line containing product with a phantom bom
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': self.product_bom.name, 'product_id': self.product_bom.id, 'product_uom_qty': 1, 'product_uom': self.product_bom.uom_id.id})],
            'pricelist_id': self.pricelist.id,
        }
        self.so = self.SaleOrder.create(so_vals)
        #confirm sale order
        self.so.action_confirm()
        #get all move associated to that sale_order
        move_ids = self.so.picking_ids.mapped('move_lines').ids
        #we should have same amount of move as the component in the phatom bom
        #bom_component_length = self.bom.explode(self.product_bom, 1, [])
        #self.assertEqual(len(move_ids), len(bom_component_length[0]))
        # We should have same amount of move as the component in the phatom bom
        #self.assertEqual(len(move_ids), 5)
