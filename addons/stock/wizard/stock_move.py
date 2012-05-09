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
import decimal_precision as dp

class stock_move_consume(osv.osv_memory):
    _name = "stock.move.consume"
    _description = "Consume Products"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True)
    }

    #TOFIX: product_uom should not have differemt category of default UOM of product. Qty should be convert into UOM of original move line before going in consume and scrap
    def default_get(self, cr, uid, fields, context=None):
        """ Get default values
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for default value
        @param context: A standard dictionary
        @return: default values of fields
        """
        if context is None:
            context = {}
        res = super(stock_move_consume, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'product_qty' in fields:
            res.update({'product_qty': move.product_qty})
        if 'location_id' in fields:
            res.update({'location_id': move.location_id.id})

        return res

    def do_move_consume(self, cr, uid, ids, context=None):
        """ To move consumed products
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        move_ids = context['active_ids']
        for data in self.browse(cr, uid, ids, context=context):
            move_obj.action_consume(cr, uid, move_ids,
                             data.product_qty, data.location_id.id,
                             context=context)
        return {'type': 'ir.actions.act_window_close'}

stock_move_consume()


class stock_move_scrap(osv.osv_memory):
    _name = "stock.move.scrap"
    _description = "Scrap Products"
    _inherit = "stock.move.consume"

    _defaults = {
        'location_id': lambda *x: False
    }

    def default_get(self, cr, uid, fields, context=None):
        """ Get default values
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for default value
        @param context: A standard dictionary
        @return: default values of fields
        """
        if context is None:
            context = {}
        res = super(stock_move_consume, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        location_obj = self.pool.get('stock.location')
        scrpaed_location_ids = location_obj.search(cr, uid, [('scrap_location','=',True)])

        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'product_qty' in fields:
            res.update({'product_qty': move.product_qty})
        if 'location_id' in fields:
            if scrpaed_location_ids:
                res.update({'location_id': scrpaed_location_ids[0]})
            else:
                res.update({'location_id': False})

        return res

    def move_scrap(self, cr, uid, ids, context=None):
        """ To move scrapped products
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        move_ids = context['active_ids']
        for data in self.browse(cr, uid, ids):
            move_obj.action_scrap(cr, uid, move_ids,
                             data.product_qty, data.location_id.id,
                             context=context)
        return {'type': 'ir.actions.act_window_close'}

stock_move_scrap()


class split_in_production_lot(osv.osv_memory):
    _name = "stock.move.split"
    _description = "Split in Serial Numbers"

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(split_in_production_lot, self).default_get(cr, uid, fields, context=context)
        if context.get('active_id'):
            move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
            if 'product_id' in fields:
                res.update({'product_id': move.product_id.id})
            if 'product_uom' in fields:
                res.update({'product_uom': move.product_uom.id})
            if 'qty' in fields:
                res.update({'qty': move.product_qty})
            if 'use_exist' in fields:
                res.update({'use_exist': (move.picking_id and move.picking_id.type=='out' and True) or False})
            if 'location_id' in fields:
                res.update({'location_id': move.location_id.id})
        return res

    _columns = {
        'qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
        'line_ids': fields.one2many('stock.move.split.lines', 'wizard_id', 'Serial Numbers'),
        'line_exist_ids': fields.one2many('stock.move.split.lines', 'wizard_exist_id', 'Serial Numbers'),
        'use_exist' : fields.boolean('Existing Lots', help="Check this option to select existing lots in the list below, otherwise you should enter new ones line by line."),
        'location_id': fields.many2one('stock.location', 'Source Location')
     }

    def split_lot(self, cr, uid, ids, context=None):
        """ To split a lot"""
        if context is None:
            context = {}
        res = self.split(cr, uid, ids, context.get('active_ids'), context=context)
        return {'type': 'ir.actions.act_window_close'}

    def split(self, cr, uid, ids, move_ids, context=None):
        """ To split stock moves into serial numbers

        :param move_ids: the ID or list of IDs of stock move we want to split
        """
        if context is None:
            context = {}
        assert context.get('active_model') == 'stock.move',\
             'Incorrect use of the stock move split wizard'
        inventory_id = context.get('inventory_id', False)
        prodlot_obj = self.pool.get('stock.production.lot')
        inventory_obj = self.pool.get('stock.inventory')
        move_obj = self.pool.get('stock.move')
        new_move = []
        for data in self.browse(cr, uid, ids, context=context):
            for move in move_obj.browse(cr, uid, move_ids, context=context):
                move_qty = move.product_qty
                quantity_rest = move.product_qty
                uos_qty_rest = move.product_uos_qty
                new_move = []
                if data.use_exist:
                    lines = [l for l in data.line_exist_ids if l]
                else:
                    lines = [l for l in data.line_ids if l]
                total_move_qty = 0.0
                for line in lines:
                    quantity = line.quantity
                    total_move_qty += quantity
                    if total_move_qty > move_qty:
                        raise osv.except_osv(_('Processing Error'), _('Serial number quantity %d of %s is larger than available quantity (%d) !') \
                                % (total_move_qty, move.product_id.name, move_qty))
                    if quantity <= 0 or move_qty == 0:
                        continue
                    quantity_rest -= quantity
                    uos_qty = quantity / move_qty * move.product_uos_qty
                    uos_qty_rest = quantity_rest / move_qty * move.product_uos_qty
                    if quantity_rest < 0:
                        quantity_rest = quantity
                        self.pool.get('stock.move').log(cr, uid, move.id, _('Unable to assign all lots to this move!'))
                        return False
                    default_val = {
                        'product_qty': quantity,
                        'product_uos_qty': uos_qty,
                        'state': move.state
                    }
                    if quantity_rest > 0:
                        current_move = move_obj.copy(cr, uid, move.id, default_val, context=context)
                        if inventory_id and current_move:
                            inventory_obj.write(cr, uid, inventory_id, {'move_ids': [(4, current_move)]}, context=context)
                        new_move.append(current_move)

                    if quantity_rest == 0:
                        current_move = move.id
                    prodlot_id = False
                    if data.use_exist:
                        prodlot_id = line.prodlot_id.id
                    if not prodlot_id:
                        prodlot_id = prodlot_obj.create(cr, uid, {
                            'name': line.name,
                            'product_id': move.product_id.id},
                        context=context)

                    move_obj.write(cr, uid, [current_move], {'prodlot_id': prodlot_id, 'state':move.state})

                    update_val = {}
                    if quantity_rest > 0:
                        update_val['product_qty'] = quantity_rest
                        update_val['product_uos_qty'] = uos_qty_rest
                        update_val['state'] = move.state
                        move_obj.write(cr, uid, [move.id], update_val)

        return new_move

split_in_production_lot()

class stock_move_split_lines_exist(osv.osv_memory):
    _name = "stock.move.split.lines"
    _description = "Stock move Split lines"
    _columns = {
        'name': fields.char('Serial Number', size=64),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'wizard_id': fields.many2one('stock.move.split', 'Parent Wizard'),
        'wizard_exist_id': fields.many2one('stock.move.split', 'Parent Wizard (for existing lines)'),
        'prodlot_id': fields.many2one('stock.production.lot', 'Serial Number'),
    }
    _defaults = {
        'quantity': 1.0,
    }

    def onchange_lot_id(self, cr, uid, ids, prodlot_id=False, product_qty=False,
                        loc_id=False, product_id=False, uom_id=False):
        return self.pool.get('stock.move').onchange_lot_id(cr, uid, [], prodlot_id, product_qty,
                        loc_id, product_id, uom_id)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
