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

        #product that has a phantom bom
        self.product_bom_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_3')[1]
        #bom with that product
        self.bom_id = self.ir_model_data.get_object_reference(cr, uid, 'mrp', 'mrp_bom_9')[1]
        #partner agrolait
        self.partner_id = self.ir_model_data.get_object_reference(cr, uid, 'base', 'res_partner_1')[1]

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
