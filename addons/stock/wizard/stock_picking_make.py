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
import netsvc

class stock_picking_make(osv.osv_memory):
    _name = 'stock.picking.make'
    _description = "Make Picking"
    
    _columns = {
        'picking_ids': fields.many2many('stock.picking', 'stock_picking_ids', 'parent_id', 'child_id', 'Pickings'),
    }

    def default_get(self, cursor, user, fields, context):
        """ 
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """ 
        res = super(stock_picking_make, self).default_get(cursor, user, fields, context=context)
        record_ids = context and context.get('active_ids',False) or False
        if record_ids:
            picking_obj = self.pool.get('stock.picking')
            picking_ids = picking_obj.search(cursor, user, [
                ('id', 'in', record_ids),
                ('state', '<>', 'done'),
                ('state', '<>', 'cancel')], context=context)
            res['picking_ids'] = picking_ids
        return res
    
    def make_packing(self, cursor, user, ids, context):
        """ 
         Make Picking.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values 
         @param context: A standard dictionary 
         @return: A dictionary which of fields with values. 
        """ 
        record_ids = context and context.get('active_ids',False) or False
        wkf_service = netsvc.LocalService('workflow')
        picking_obj = self.pool.get('stock.picking')
        data = self.read(cursor, user, ids[0])
        pick_ids = data['picking_ids']
        picking_obj.force_assign(cursor, user, pick_ids)
        picking_obj.action_move(cursor, user, pick_ids)
        for picking_id in ids:
            wkf_service.trg_validate(user, 'stock.picking', picking_id,
                    'button_done', cursor)
        return {}

stock_picking_make()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

