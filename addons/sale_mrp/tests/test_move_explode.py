# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tests import common


class TestMoveExplode(common.TransactionCase):

    def setUp(self):
        super(TestMoveExplode, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.ir_model_data = self.registry('ir.model.data')
        self.sale_order_line = self.registry('sale.order.line')
        self.sale_order = self.registry('sale.order')
        self.mrp_bom = self.registry('mrp.bom')
        self.product = self.registry('product.product')

        #product that has a phantom bom
        self.product_bom_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_3')[1]
        #bom with that product
        self.bom_id = self.ir_model_data.get_object_reference(cr, uid, 'mrp', 'mrp_bom_9')[1]
        #partner agrolait
        self.partner_id = self.ir_model_data.get_object_reference(cr, uid, 'base', 'res_partner_1')[1]
        #bom: PC Assemble (with property: DDR 512MB)
        self.bom_prop_id = self.ir_model_data.get_object_reference(cr, uid, 'mrp', 'mrp_bom_property_0')[1]

        self.template_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_3_product_template')[1]
        #property: DDR 512MB
        self.mrp_property_id = self.ir_model_data.get_object_reference(cr, uid, 'mrp', 'mrp_property_0')[1]
        #product: RAM SR2
        self.product_bom_prop_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_14')[1]
        #phantom bom for RAM SR2 with three lines containing properties
        self.bom_prop_line_id = self.ir_model_data.get_object_reference(cr, uid, 'mrp', 'mrp_bom_property_line')[1]
        #product: iPod included in the phantom bom
        self.product_A_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_11')[1]
        #product: Mouse, Wireless included in the phantom bom
        self.product_B_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_12')[1]


    def test_00_sale_move_explode(self):
        """check that when creating a sale order with a product that has a phantom BoM, move explode into content of the
            BoM"""
        cr, uid, context = self.cr, self.uid, {}
        #create sale order with one sale order line containing product with a phantom bom
        so_id = self.sale_order.create(cr, uid, vals={'partner_id': self.partner_id}, context=context)
        self.sale_order_line.create(cr, uid, values={'order_id': so_id, 'product_id': self.product_bom_id, 'product_uom_qty': 1}, context=context)
        #confirm sale order
        self.sale_order.action_button_confirm(cr, uid, [so_id], context=context)
        #get all move associated to that sale_order
        browse_move_ids = self.sale_order.browse(cr, uid, so_id, context=context).picking_ids[0].move_lines
        move_ids = [x.id for x in browse_move_ids]
        #we should have same amount of move as the component in the phatom bom
        bom = self.mrp_bom.browse(cr, uid, self.bom_id, context=context)
        bom_component_length = self.mrp_bom._bom_explode(cr, uid, bom, self.product_bom_id, 1, [])
        self.assertEqual(len(move_ids), len(bom_component_length[0]))

    def test_00_bom_find(self):
        """Check that _bom_find searches the bom corresponding to the properties passed or takes the bom with the smallest
            sequence."""
        cr, uid, context = self.cr, self.uid, {}
        res_id = self.mrp_bom._bom_find(cr, uid, product_tmpl_id=self.template_id, product_id=None, properties=[self.mrp_property_id], context=context)
        self.assertEqual(res_id, self.bom_prop_id)

    def test_00_bom_explode(self):
        """Check that _bom_explode only takes the lines with the right properties."""
        cr, uid, context = self.cr, self.uid, {}
        bom = self.mrp_bom.browse(cr, uid, self.bom_prop_line_id)
        product = self.product.browse(cr, uid, self.product_bom_prop_id)
        res = self.mrp_bom._bom_explode(cr, uid, bom, product, 1, properties=[self.mrp_property_id], context=context)
        res = set([p['product_id'] for p in res[0]])
        self.assertEqual(res, set([self.product_A_id, self.product_B_id]))
