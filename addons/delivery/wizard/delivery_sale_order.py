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

import time
from tools.translate import _

from osv import osv, fields

class make_delivery(osv.osv_memory):
    _name = "delivery.sale.order"
    _description = 'Make Delievery'

    _columns = {
        'carrier_id': fields.many2one('delivery.carrier','Delivery Method', required=True),
    }


    def default_get(self, cr, uid, fields, context=None):
        """ 
             To get default values for the object.
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param fields: List of fields for which we want default values 
             @param context: A standard dictionary 
             
             @return: A dictionary which of fields with values. 
        
        """
        res = super(make_delivery, self).default_get(cr, uid, fields, context=context)
        order_obj = self.pool.get('sale.order')
        for order in order_obj.browse(cr, uid, context.get('active_ids', []), context=context):
             carrier = order.carrier_id.id
             if not carrier:
                  carrier = order.partner_id.property_delivery_carrier.id
             res.update({'carrier_id': carrier})
             
        return res
    
    def view_init(self, cr , uid , fields, context=None):
         if context is None:
            context = {}
         order_obj = self.pool.get('sale.order')
         for order in order_obj.browse(cr, uid, context.get('active_ids', []), context=context):     
             if not order.state in ('draft'):
                 raise osv.except_osv(_('Order not in draft state !'), _('The order state have to be draft to add delivery lines.'))
         pass     
        
    def delivery_set(self, cr, uid, ids, context=None):
        """ 
             Adds delivery costs to Sale Order Line.
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: List of IDs selected 
             @param context: A standard dictionary 
             
             @return:  
        
        """
        if context is None:
            context = {}
        rec_ids = context and context.get('active_ids',[])
        order_obj = self.pool.get('sale.order')
        line_obj = self.pool.get('sale.order.line')
        grid_obj = self.pool.get('delivery.grid')
        carrier_obj = self.pool.get('delivery.carrier')
        acc_fp_obj = self.pool.get('account.fiscal.position')
        order_objs = order_obj.browse(cr, uid, rec_ids, context=context)
        for datas in self.browse(cr, uid, ids, context=context):    
            for order in order_objs:
                grid_id = carrier_obj.grid_get(cr, uid, [datas.carrier_id.id],order.partner_shipping_id.id)
                if not grid_id:
                    raise osv.except_osv(_('No grid available !'), _('No grid matching for this carrier !'))

                if not order.state in ('draft'):
                    raise osv.except_osv(_('Order not in draft state !'), _('The order state have to be draft to add delivery lines.'))
                
                grid = grid_obj.browse(cr, uid, grid_id, context=context)
        
                taxes = grid.carrier_id.product_id.taxes_id
                fpos = order.fiscal_position or False
                taxes_ids = acc_fp_obj.map_tax(cr, uid, fpos, taxes)
                line_obj.create(cr, uid, {
                    'order_id': order.id,
                    'name': grid.carrier_id.name,
                    'product_uom_qty': 1,
                    'product_uom': grid.carrier_id.product_id.uom_id.id,
                    'product_id': grid.carrier_id.product_id.id,
                    'price_unit': grid_obj.get_price(cr, uid, grid.id, order, time.strftime('%Y-%m-%d'), context),
                    'tax_id': [(6,0,taxes_ids)],
                    'type': 'make_to_stock'
                })
    
        return {'type': 'ir.actions.act_window_close'}

make_delivery()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

