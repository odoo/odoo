# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


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
        #bom:  (with property: DDR 512MB)
        self.bom_prop = self.env.ref('mrp.mrp_bom_manufacture')
        self.bom_prop.write({'property_ids': [(6,0,[self.env['ir.model.data'].xmlid_to_res_id('mrp.mrp_property_8')])]})

        self.template = self.env.ref('product.product_product_3_product_template')
        self.mrp_property = self.env.ref('mrp.mrp_property_8')
        self.product_bom_prop = self.env.ref('product.product_product_5')
        #phantom bom for 17 with seven lines containing properties
        self.bom_prop_line = self.env.ref('mrp.mrp_bom_kit')
        # write different properties on the bom and on 2 bom lines
        self.bom_prop_line.write({'property_ids': [(6,0,[self.env['ir.model.data'].xmlid_to_res_id('mrp.mrp_property_0')])], 'product_id': self.env['ir.model.data'].xmlid_to_res_id('product.product_product_5')})
        #product: Motherboard included in the phantom bom
        self.product_A = self.env.ref('product.product_product_20')
        #product: 24 Graphic card in the phantom bom
        self.product_B = self.env.ref('product.product_product_24')
        for bom_line in self.bom_prop_line.bom_line_ids:
            if bom_line.product_id.id in [self.env.ref('product.product_product_20').id, self.env.ref('product.product_product_24').id]:
                bom_line.write({'property_ids': [(6, 0, [self.env['ir.model.data'].xmlid_to_res_id('mrp.mrp_property_8')])]})
            else:
                bom_line.write({'property_ids': [(6, 0, [self.env['ir.model.data'].xmlid_to_res_id('mrp.mrp_property_0')])]})
        #pricelist
        self.pricelist = self.env.ref('product.list0')


    def test_00_sale_move_explode(self):
        """check that when creating a sale order with a product that has a phantom BoM, move explode into content of the
            BoM"""
        # Remove properties on the bom an on the bom lines
        self.bom.write({'property_ids': [(6,0,[])]})
        for line in self.bom.bom_line_ids:
            line.write({'property_ids': [(6,0,[])]})
        # Create sale order with one sale order line containing product with a phantom bom
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': self.product_bom.name, 'product_id': self.product_bom.id, 'product_uom_qty': 1, 'product_uom': self.product_bom.uom_id.id})],
            'pricelist_id': self.pricelist.id,
        }
        self.so = self.SaleOrder.create(vals=so_vals)
        #confirm sale order
        self.so.action_confirm()
        #get all move associated to that sale_order
        move_ids = self.so.picking_ids.mapped('move_lines').ids
        #we should have same amount of move as the component in the phatom bom
        bom_component_length = self.MrpBom._bom_explode(self.bom, self.product_bom, 1.0, properties=[])
        self.assertEqual(len(move_ids), len(bom_component_length[0]))

    def test_00_bom_find(self):
        """Check that _bom_find searches the bom corresponding to the properties passed or takes the bom with the smallest
            sequence."""
        res_id = self.MrpBom._bom_find(product_tmpl_id=self.template.id, product_id=None, properties=[self.mrp_property.id])
        self.assertEqual(res_id, self.bom_prop.id)

    def test_00_bom_explode(self):
        """Check that _bom_explode only takes the lines with the right properties."""
        res = self.MrpBom._bom_explode(self.bom_prop_line, self.product_bom_prop, 1, properties=[self.mrp_property.id])
        res = set([p['product_id'] for p in res[0]])
        self.assertEqual(res, set([self.product_A.id, self.product_B.id]))
