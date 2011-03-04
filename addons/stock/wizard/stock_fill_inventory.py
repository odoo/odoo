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

class stock_fill_inventory(osv.osv_memory):
    _name = "stock.fill.inventory"
    _description = "Import Inventory"
    _columns = {
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'recursive': fields.boolean("Include children",help="If checked, products contained in child locations of selected location will be included as well."),
        'set_stock_zero': fields.boolean("Set to zero",help="If checked, all product quantities will be set to zero to help ensure a real physical inventory is done"),
    }
    def view_init(self, cr, uid, fields_list, context=None):
        """
         Creates view dynamically and adding fields at runtime.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: New arch of view with new columns.
        """
        if context==None:
            context={}
        res = super(stock_fill_inventory, self).view_init(cr, uid, fields_list, context=context)
        if context.get('active_id', False):
            stock = self.pool.get('stock.inventory').browse(cr, uid, context.get('active_id', False))
            if stock.state=='done':
                raise osv.except_osv(_('Error!'), _('Stock Inventory is done'))
        True

    def fill_inventory(self, cr, uid, ids, context=None):
        """ To Import stock inventory according to products available in the selected locations.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        inventory_line_obj = self.pool.get('stock.inventory.line')
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        stock_location_obj = self.pool.get('stock.location')
        move_obj = self.pool.get('stock.move')
        if ids and len(ids):
            ids = ids[0]
        else:
             return {'type': 'ir.actions.act_window_close'}
        fill_inventory = self.browse(cr, uid, ids, context=context)
        res = {}
        res_location = {}
        if fill_inventory.recursive :
            location_ids = location_obj.search(cr, uid, [('location_id',
                             'child_of', fill_inventory.location_id.id)])
            for location in location_ids :
                res = location_obj._product_get(cr, uid, location)
                res_location[location] = res
        else:
            context.update({'compute_child': False})
            res = location_obj._product_get(cr, uid,
                        fill_inventory.location_id.id, context=context)
            res_location[fill_inventory.location_id.id] = res

        product_ids = []
        res = {}
        for location in res_location.keys():
            datas = {}
            res[location] = {}
            if fill_inventory.recursive :
                move_ids = move_obj.search(cr, uid, [('location_dest_id','child_of',location),('state','=','done')], context=context)
            else:
                move_ids = move_obj.search(cr, uid, [('location_dest_id','=',location),('state','=','done')], context=context)
            if not move_ids:
                raise osv.except_osv(_('Message !'), _('No product in this location.'))

            for move in move_obj.browse(cr, uid, move_ids, context=context):
                lot_id = move.prodlot_id.id
                prod_id = move.product_id.id
                qty = move.product_qty
                location_dest_id = move.location_dest_id.id
                if datas.get((prod_id, lot_id)):
                    qty = datas[(prod_id, lot_id)]['product_qty'] + qty
                datas[(prod_id, lot_id)] = {'product_id': prod_id, 'location_dest_id': location_dest_id, 'product_qty': qty, 'product_uom': move.product_id.uom_id.id, 'prodlot_id': lot_id}
            res[location] = datas

            for i in datas.items():
                if(i[1]['product_qty']):
                    if fill_inventory.set_stock_zero:
                        i[1]['product_qty'] = 0

                    line_ids = inventory_line_obj.search(cr, uid,
                        [('inventory_id','=', context['active_ids']),
                         ('location_id','=', i[1]['location_dest_id']),
                         ('product_id','=', i[1]['product_id']),
                         ('product_uom','=', i[1]['product_uom']),
                         ('product_qty','=', i[1]['product_qty']),
                         ('prod_lot_id','=', i[1]['prodlot_id'])
                         ])
                    if not len(line_ids):
                        inventory_line = {
                            'inventory_id': context['active_ids'][0],
                            'location_id': i[1]['location_dest_id'],
                            'product_id': i[1]['product_id'],
                            'product_uom': i[1]['product_uom'],
                            'product_qty': i[1]['product_qty'],
                            'prod_lot_id': i[1]['prodlot_id']
                        }
                        inventory_line_obj.create(cr, uid, inventory_line)

            return {'type': 'ir.actions.act_window_close'}

stock_fill_inventory()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
