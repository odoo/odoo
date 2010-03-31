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
import netsvc
import pooler
import time
import wizard
from osv.orm import browse_record, browse_null

class purchase_order_group(osv.osv_memory):
    _name = "purchase.order.group"
    _description = "Purchase Wizard"
    _columns = {
          
        } 

    def merge_orders(self, cr, uid, ids, context):
        """ 
             To merge similar type of purchase orders.
            
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs 
             @param context: A standard dictionary 
             
             @return: purchase order view
            
        """              
        order_obj = self.pool.get('purchase.order')
        mod_obj =self.pool.get('ir.model.data')
        result = mod_obj._get_id(cr, uid, 'purchase', 'view_purchase_order_filter')
        id = mod_obj.read(cr, uid, result, ['res_id'])
      

        allorders = order_obj.do_merge(cr, uid, context.get('active_ids',[]), context)
        

        return {
        'domain': "[('id','in', [" + ','.join(map(str, allorders)) + "])]",
        'name': 'Purchase Orders',
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'purchase.order',
        'view_id': False,
        'type': 'ir.actions.act_window',
        'search_view_id': id['res_id']
        }
purchase_order_group()

