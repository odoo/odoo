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
import time

class stock_inventory_line_split(osv.osv_memory):
    _inherit = "stock.move.split"
    _name = "stock.inventory.line.split"
    _description = "Split inventory lines"


    def default_get(self, cr, uid, fields, context=None):
        """ To check the availability of production lot.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values
        @param context: A standard dictionary
        @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        record_id = context and context.get('active_id',False)
        res = {}
        line = self.pool.get('stock.inventory.line').browse(cr, uid, record_id, context=context)
        if 'product_id' in fields:
            res.update({'product_id':line.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': line.product_uom.id})
        if 'qty' in fields:
            res.update({'qty': line.product_qty})
        return res

    def split(self, cr, uid, ids, line_ids, context=None):
        """ To split stock inventory lines according to production lot.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param line_ids: the ID or list of IDs of inventory lines we want to split
        @param context: A standard dictionary
        @return:
        """
        prodlot_obj = self.pool.get('stock.production.lot')
        ir_sequence_obj = self.pool.get('ir.sequence')
        line_obj = self.pool.get('stock.inventory.line')
        new_line = []
        for data in self.browse(cr, uid, ids, context=context):
            for inv_line in line_obj.browse(cr, uid, line_ids, context=context):
                line_qty = inv_line.product_qty
                quantity_rest = inv_line.product_qty
                new_line = []
                if data.use_exist:
                    lines = [l for l in data.line_exist_ids if l]
                else:
                    lines = [l for l in data.line_ids if l]
                for line in lines:
                    quantity = line.quantity
                    if quantity <= 0 or line_qty == 0:
                        continue
                    quantity_rest -= quantity
                    if quantity_rest < 0:
                        quantity_rest = quantity
                        break
                    default_val = {
                        'product_qty': quantity,
                    }
                    if quantity_rest > 0:
                        current_line = line_obj.copy(cr, uid, inv_line.id, default_val)
                        new_line.append(current_line)
                    if quantity_rest == 0:
                        current_line = inv_line.id
                    prodlot_id = False
                    if data.use_exist:
                        prodlot_id = line.prodlot_id.id
                    if not prodlot_id:
                        prodlot_id = prodlot_obj.create(cr, uid, {
                            'name': line.name,
                            'product_id': inv_line.product_id.id},
                        context=context)
                    line_obj.write(cr, uid, [current_line], {'prod_lot_id': prodlot_id})
                    prodlot = prodlot_obj.browse(cr, uid, prodlot_id)

                    update_val = {}
                    if quantity_rest > 0:
                        update_val['product_qty'] = quantity_rest
                        line_obj.write(cr, uid, [inv_line.id], update_val)

        return new_line
stock_inventory_line_split()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

