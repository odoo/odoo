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
from tools.translate import _

class stock_inventory_merge(osv.osv_memory):
    _name = "stock.inventory.merge"
    _description = "Merge Inventory"
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', 
                        context=None, toolbar=False, submenu=False):
        """ 
         Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary 
         @return: New arch of view.
        """
        if context is None:
            context={}
        res = super(stock_inventory_merge, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if context.get('active_model','') == 'stock.inventory' and len(context['active_ids']) < 2:
            raise osv.except_osv(_('Warning!'),
            _('Please select multiple physical inventories to merge in the list view.'))
        return res    
        
    def do_merge(self, cr, uid, ids, context=None):
        """ To merge selected Inventories.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected 
        @param context: A standard dictionary 
        @return: 
        """ 
        invent_obj = self.pool.get('stock.inventory')
        invent_line_obj = self.pool.get('stock.inventory.line')
        invent_lines = {}
        if context is None:
            context = {}
        for inventory in invent_obj.browse(cr, uid, context['active_ids'], context=context):
            if inventory.state == "done":
                raise osv.except_osv(_('Warning!'),
                _('Merging is only allowed on draft inventories.'))

            for line in inventory.inventory_line_id:
                key = (line.location_id.id, line.product_id.id, line.product_uom.id)
                if key in invent_lines:
                    invent_lines[key] += line.product_qty
                else:
                    invent_lines[key] = line.product_qty


        new_invent = invent_obj.create(cr, uid, {
            'name': 'Merged inventory'
            }, context=context)

        for key, quantity in invent_lines.items():
            invent_line_obj.create(cr, uid, {
                    'inventory_id': new_invent,
                    'location_id': key[0],
                    'product_id': key[1],
                    'product_uom': key[2],
                    'product_qty': quantity,
                })

        return {'type': 'ir.actions.act_window_close'}

stock_inventory_merge()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

