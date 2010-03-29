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

from osv import fields, osv
from service import web_services
from tools.misc import UpdateableStr, UpdateableDict
from tools.translate import _
import netsvc
import pooler
import time
import wizard


class inventory_set_stock_zero(osv.osv_memory):
    _name = "stock.inventory.set.stock.zero"
    _description = "Set Stock to 0"
    _columns = {
            'location_id': fields.many2one('stock.location', 'Location', required=True), 
            }
    
    def do_merge(self, cr, uid, ids, context):
        """ 
             To set stock to Zero 
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one 
             @param context: A standard dictionary 
             
             @return:  
        
        """            
        invent_obj = pooler.get_pool(cr.dbname).get('stock.inventory')
        invent_line_obj = pooler.get_pool(cr.dbname).get('stock.inventory.line')
        prod_obj =  pooler.get_pool(cr.dbname).get('product.product')
    
        if len(context['active_ids']) <> 1:
            raise osv.except_osv(_('Warning'), 
                                       _('Please select one and only one inventory !'))
        for id in ids:
            datas = self.read(cr, uid, id)
            loc = str(datas['location_id'])
        
            cr.execute('select distinct location_id,product_id \
                        from stock_inventory_line \
                        where inventory_id=%s', (context['active_id'],))
            inv = cr.fetchall()
            cr.execute('select distinct product_id from stock_move where \
                        location_dest_id=%s or location_id=%s', (loc, loc,))
            stock = cr.fetchall()
            for s in stock:
                if (loc, s[0]) not in inv:
                    p = prod_obj.browse(cr, uid, s[0])
                    invent_line_obj.create(cr, uid, {
                        'inventory_id': context['active_id'], 
                        'location_id': loc, 
                        'product_id': s[0], 
                        'product_uom': p.uom_id.id, 
                        'product_qty': 0.0, 
                        })
        return {}

inventory_set_stock_zero()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
