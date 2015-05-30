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

from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp.tools import mute_logger

class stock_fill_inventory(osv.osv_memory):
    _name = "stock.fill.inventory"
    _description = "Import Inventory"

    # Maximum size of a batch of lines we can import without risking OOM
    MAX_IMPORT_LINES = 10000

    def _default_location(self, cr, uid, ids, context=None):
        try:
            location = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_stock')
            with mute_logger('openerp.osv.orm'):
                location.check_access_rule('read', context=context)
            location_id = location.id
        except (ValueError, orm.except_orm), e:
            return False
        return location_id or False

    _columns = {
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'recursive': fields.boolean("Include children",help="If checked, products contained in child locations of selected location will be included as well."),
        'set_stock_zero': fields.boolean("Set to zero",help="If checked, all product quantities will be set to zero to help ensure a real physical inventory is done"),
    }
    _defaults = {
        'location_id': _default_location,
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
        if context is None:
            context = {}
        super(stock_fill_inventory, self).view_init(cr, uid, fields_list, context=context)

        if len(context.get('active_ids',[])) > 1:
            raise osv.except_osv(_('Error!'), _('You cannot perform this operation on more than one Stock Inventories.'))

        if context.get('active_id', False):
            stock = self.pool.get('stock.inventory').browse(cr, uid, context.get('active_id', False))
        return True

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
        move_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        if ids and len(ids):
            ids = ids[0]
        else:
             return {'type': 'ir.actions.act_window_close'}
        fill_inventory = self.browse(cr, uid, ids, context=context)
        res = {}
        res_location = {}

        if fill_inventory.recursive:
            location_ids = location_obj.search(cr, uid, [('location_id',
                             'child_of', [fill_inventory.location_id.id])], order="id",
                             context=context)
        else:
            location_ids = [fill_inventory.location_id.id]

        res = {}
        flag = False

        for location in location_ids:
            datas = {}
            res[location] = {}
            all_move_ids = move_obj.search(cr, uid, ['|',('location_dest_id','=',location),('location_id','=',location),('state','=','done')], context=context)
            local_context = dict(context)
            local_context['raise-exception'] = False
            # To avoid running out of memory, process limited batches
            for i in xrange(0, len(all_move_ids), self.MAX_IMPORT_LINES):
                move_ids = all_move_ids[i:i+self.MAX_IMPORT_LINES]
                for move in move_obj.browse(cr, uid, move_ids, context=context):
                    lot_id = move.prodlot_id.id
                    prod_id = move.product_id.id
                    if move.location_dest_id.id != move.location_id.id:
                        if move.location_dest_id.id == location:
                            qty = uom_obj._compute_qty_obj(cr, uid, move.product_uom,move.product_qty, move.product_id.uom_id, context=local_context)
                        else:
                            qty = -uom_obj._compute_qty_obj(cr, uid, move.product_uom,move.product_qty, move.product_id.uom_id, context=local_context)


                        if datas.get((prod_id, lot_id)):
                            qty += datas[(prod_id, lot_id)]['product_qty']

                        # Floating point sum could introduce tiny rounding errors :
                        #     Use the UoM API for the rounding (same UoM in & out).
                        qty = uom_obj._compute_qty_obj(cr, uid,
                                                       move.product_id.uom_id, qty,
                                                       move.product_id.uom_id)
                        datas[(prod_id, lot_id)] = {'product_id': prod_id, 'location_id': location, 'product_qty': qty, 'product_uom': move.product_id.uom_id.id, 'prod_lot_id': lot_id}

            if datas:
                flag = True
                res[location] = datas

        if not flag:
            raise osv.except_osv(_('Warning!'), _('No product in this location. Please select a location in the product form.'))

        for stock_move in res.values():
            for stock_move_details in stock_move.values():
                stock_move_details.update({'inventory_id': context['active_ids'][0]})
                domain = []
                for field, value in stock_move_details.items():
                    if field == 'product_qty' and fill_inventory.set_stock_zero:
                         domain.append((field, 'in', [value,'0']))
                         continue
                    domain.append((field, '=', value))

                if fill_inventory.set_stock_zero:
                    stock_move_details.update({'product_qty': 0})

                line_ids = inventory_line_obj.search(cr, uid, domain, context=context)

                if not line_ids:
                    inventory_line_obj.create(cr, uid, stock_move_details, context=context)

        return {'type': 'ir.actions.act_window_close'}

stock_fill_inventory()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
