# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class purchase_order(osv.osv):
    _inherit = 'purchase.order'
     
    def action_picking_create(self, cr, uid, ids, context=None):
        # if invoice method is 'picking' then do not allow to confirm PO
        # what you should check is:
        #- is the purchase and sale order linked to the same picking ?
        #- is the sale order with invoice_method picking
        #- is the purchase order with invoice_method picking
        # group_id name is Sale_reference
        # picking Origin = PO name
        # Picking Type Id = Drop shipping
        # Did not get picking id
        if not context: context = {}
        super(purchase_order, self).action_picking_create(cr, uid, ids, context=context)
        sale_obj = self.pool.get('sale.order')
        picking_obj = self.pool.get('stock.picking')
        for order in self.browse(cr, uid, ids, context=context):
            for picking_id in order.picking_ids:
                sale_ids = sale_obj.search(cr, uid, [('procurement_group_id','=', picking_id.group_id.id)], context=context)
                if sale_ids:
                    for sale_order in sale_obj.browse(cr, uid, sale_ids, context=context):
                    	for sale_picking_id in sale_order.picking_ids:
                            if picking_id.id == sale_picking_id.id:
                                if order.invoice_method == 'picking' and sale_order.order_policy == 'picking':
                                # we can also check the commented condition in case of drop shipping
                                #if order.picking_ids.id == sale_order.picking_ids.id and order.picking_ids.group_id.name == sale_order.name \
                                #and order.picking_ids.origin == order.name and order.picking_ids.picking_type_id.sequence_id.name == 'Dropship':
                                	raise osv.except_osv(_( 'Warning!'), _('You can not have both sale and purchase order with invoice policy on delivery'))



