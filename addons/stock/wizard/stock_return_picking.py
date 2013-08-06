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

from openerp.osv import osv,fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class stock_return_picking_line(osv.osv_memory):
    _name = "stock.return.picking.line"
    _rec_name = 'product_id'

    def _get_lot_id(self, cr, uid, ids, name, args, context=None):
        res = {}.fromkeys(ids, {'lot_id': False})
        for element in self.browse(cr, uid, ids, context=context):
            if element.move_id and element.move_id.quant_ids:
                res[element.id]['lot_id'] = element.move_id.quant_ids[0].lot_id and element.move_id.quant_ids[0].lot_id.id or False
        return res

    _columns = {
        'product_id' : fields.many2one('product.product', string="Product", required=True),
        'quantity' : fields.float("Quantity", digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'wizard_id' : fields.many2one('stock.return.picking', string="Wizard"),
        'move_id' : fields.many2one('stock.move', "Move"),
        'lot_id': fields.function(_get_lot_id, type="many2one", relation='stock.production.lot', string='Serial Number', readonly=True),
    }



class stock_return_picking(osv.osv_memory):
    _name = 'stock.return.picking'
    _description = 'Return Picking'
    _columns = {
        'product_return_moves' : fields.one2many('stock.return.picking.line', 'wizard_id', 'Moves'),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        result1 = []
        if context is None:
            context = {}
        res = super(stock_return_picking, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        if pick:
            for line in pick.move_lines:
                qty = line.product_uom_qty
                current_qty_returned = 0
                if line.returned_move_ids:
                    for returned_move in line.returned_move_ids:
                        if returned_move.product_id.id == line.product_id.id:
                            current_qty_returned += returned_move.product_uom_qty
                
                if qty > 0 and current_qty_returned < qty:
                    result1.append({'product_id': line.product_id.id, 'quantity': qty-current_qty_returned,'move_id':line.id, 'lot_id': line.quant_ids[0].lot_id and line.quant_ids[0].lot_id.id or False})
            if 'product_return_moves' in fields:
                res.update({'product_return_moves': result1})
        return res

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
        res = super(stock_return_picking, self).view_init(cr, uid, fields_list, context=context)
        record_id = context and context.get('active_id', False)
        if record_id:
            pick_obj = self.pool.get('stock.picking')
            pick = pick_obj.browse(cr, uid, record_id, context=context)
            if pick.state not in ['done','confirmed','assigned']:
                raise osv.except_osv(_('Warning!'), _("You may only return pickings that are Confirmed, Available or Done!"))
            valid_lines = 0
            for line  in pick.move_lines:
                qty = line.product_uom_qty
                current_qty_returned = 0
                if line.returned_move_ids:
                    for returned_move in line.returned_move_ids:
                        if returned_move.product_id.id == line.product_id.id:
                            current_qty_returned += returned_move.product_uom_qty
                if line.state == 'done' and current_qty_returned < qty:
                    valid_lines += 1
            if not valid_lines:
                raise osv.except_osv(_('Warning!'), _("No products to return (only lines in Done state and not fully returned yet can be returned)!"))
        return res

    def create_returns(self, cr, uid, ids, context=None):
        """ 
         Creates return picking.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids selected
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {} 
        record_id = context and context.get('active_id', False) or False
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        data_obj = self.pool.get('stock.return.picking.line')
        act_obj = self.pool.get('ir.actions.act_window')
        model_obj = self.pool.get('ir.model.data')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        data = self.read(cr, uid, ids[0], context=context)
        date_cur = time.strftime('%Y-%m-%d %H:%M:%S')
        returned_lines = 0
        
#        Create new picking for returned products
        new_picking = pick_obj.copy(cr, uid, pick.id, {
                                        'move_lines': [], 
                                        'state':'draft', 
                                        'date':date_cur,
        })
        new_pick_name = pick_obj.browse(cr, uid, new_picking, context=context).name
        pick_obj.write(cr, uid, new_picking, {'name': _('%s-%s-return') % (new_pick_name, pick.name)}, context=context)
        
        val_id = data['product_return_moves']
        for v in val_id:
            data_get = data_obj.browse(cr, uid, v, context=context)
            mov_id = data_get.move_id.id
            if not mov_id:
                raise osv.except_osv(_('Warning !'), _("You have manually created product lines, please delete them to proceed"))
            new_qty = data_get.quantity
            move = move_obj.browse(cr, uid, mov_id, context=context)
            new_location = move.location_dest_id.id
            if new_qty:
                returned_lines += 1
                quant_ids = []
                for quant in move.quant_ids:
                    quant_ids.append((4,quant.id))
                new_move=move_obj.copy(cr, uid, move.id, {
                                            'product_id': data_get.product_id.id,
                                            'product_uom_qty': new_qty,
                                            'product_uos_qty': uom_obj._compute_qty(cr, uid, move.product_uom.id, new_qty, move.product_uos.id),
                                            'picking_id': new_picking, 
                                            'state': 'draft',
                                            'location_id': new_location, 
                                            'location_dest_id': move.location_id.id,
                                            'date': date_cur,
                                            'reserved_quant_ids':quant_ids,
                                            'origin_returned_move_id': move.id,
                })
                move_obj.write(cr, uid, move.id, {'returned_move_ids':[(4,new_move)]}, context=context)
        if not returned_lines:
            raise osv.except_osv(_('Warning!'), _("Please specify at least one non-zero quantity."))

        pick_obj.action_confirm(cr, uid, [new_picking], context=context)
        pick_obj.force_assign(cr, uid, [new_picking], context)
        return {
            'domain': "[('id', 'in', ["+str(new_picking)+"])]",
            'name': _('Returned Picking'),
            'view_type':'form',
            'view_mode':'tree,form',
            'res_model': 'stock.picking',
            'type':'ir.actions.act_window',
            'context':context,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
