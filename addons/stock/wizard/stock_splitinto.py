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


class stock_split_into(osv.osv_memory):
    _name = "stock.split.into"
    _description = "Split into"

    def default_get(self, cr, uid, fields, context=None):
        """ Get default values
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for default value
        @param context: A standard dictionary
        @return: Default values of fields
        """
        res = super(stock_split_into, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        if 'quantity' in fields:
            res.update({'quantity': move.product_qty})
        return res

    _columns = {
        'quantity': fields.integer('Quantity'),
    }
    _defaults = {
        'quantity': lambda *x: 1,
    }

    def split(self, cr, uid, data, context=None):
        rec_id = context and context.get('active_ids', False)
        move_obj = self.pool.get('stock.move')
        new_move = []
        update_val = {}
        value_to_split = self.browse(cr, uid, data[0], context)
        quantity =  value_to_split.quantity or 0.0
        ir_sequence_obj = self.pool.get('ir.sequence')
        track_obj = self.pool.get('stock.tracking')
        for move in move_obj.browse(cr, uid, rec_id):
            move_qty = move.product_qty
            uos_qty_rest = move.product_uos_qty
            quantity_rest = move_qty - quantity
            if quantity_rest == 0:
                continue
            sequence = ir_sequence_obj.get(cr, uid, 'stock.lot.tracking')
            tracking_id = track_obj.create(cr, uid, {'name': sequence}, {'product_id': move.product_id.id})
            uos_qty = quantity / move_qty * move.product_uos_qty
            uos_qty_rest = quantity_rest / move_qty * move.product_uos_qty
            default_val = {
                'product_qty': quantity,
                'product_uos_qty': uos_qty,
                'state': move.state
            }
            current_move = move_obj.copy(cr, uid, move.id, default_val)
            new_move.append(current_move)
            update_val['product_qty'] = quantity_rest
            update_val['tracking_id'] = tracking_id
            update_val['product_uos_qty'] = uos_qty_rest
            move_obj.write(cr, uid, [move.id], update_val)
        return {}
stock_split_into()

