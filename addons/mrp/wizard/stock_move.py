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

from openerp.osv import fields, osv
from openerp.tools import float_compare
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class stock_move_consume(osv.osv_memory):
    _name = "stock.move.consume"
    _description = "Consume Products"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'restrict_lot_id': fields.many2one('stock.production.lot', 'Lot'),
    }

    #TOFIX: product_uom should not have different category of default UOM of product. Qty should be convert into UOM of original move line before going in consume and scrap
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(stock_move_consume, self).default_get(cr, uid, fields, context=context)
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'product_qty' in fields:
            res.update({'product_qty': move.product_uom_qty})
        if 'location_id' in fields:
            res.update({'location_id': move.location_id.id})
        return res



    def do_move_consume(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        production_obj = self.pool.get('mrp.production')
        move_ids = context['active_ids']
        move = move_obj.browse(cr, uid, move_ids[0], context=context)
        production_id = move.raw_material_production_id.id
        production = production_obj.browse(cr, uid, production_id, context=context)
        precision = self.pool['decimal.precision'].precision_get(cr, uid, 'Product Unit of Measure')

        for data in self.browse(cr, uid, ids, context=context):
            qty = uom_obj._compute_qty(cr, uid, data['product_uom'].id, data.product_qty, data.product_id.uom_id.id)
            remaining_qty = move.product_qty - qty
            #check for product quantity is less than previously planned
            if float_compare(remaining_qty, 0, precision_digits=precision) >= 0:
                move_obj.action_consume(cr, uid, move_ids, qty, data.location_id.id, restrict_lot_id=data.restrict_lot_id.id, context=context)
            else:
                consumed_qty = min(move.product_qty, qty)
                new_moves = move_obj.action_consume(cr, uid, move_ids, consumed_qty, data.location_id.id, restrict_lot_id=data.restrict_lot_id.id, context=context)
                #consumed more in wizard than previously planned
                extra_more_qty = qty - consumed_qty
                #create new line for a remaining qty of the product
                extra_move_id = production_obj._make_consume_line_from_data(cr, uid, production, data.product_id, data.product_id.uom_id.id, extra_more_qty, False, 0, context=context)
                move_obj.write(cr, uid, [extra_move_id], {'restrict_lot_id': data.restrict_lot_id.id}, context=context)
                move_obj.action_done(cr, uid, [extra_move_id], context=context)

        return {'type': 'ir.actions.act_window_close'}