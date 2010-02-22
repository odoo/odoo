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
import netsvc

class stock_move_produce(osv.osv_memory):
    _name = "stock.move.produce"
    _description = "Produce"
    
    _columns = {
        'product_qty': fields.float('Quantity', required=True), 
        'mode': fields.selection([('consume_produce', 'Consumme & Produce'), 
                                  ('consume', 'Consumme Only')], 'Mode', required=True)
              }

    def _get_product_qty(self, cr, uid, context):
        prod = self.pool.get('mrp.production').browse(cr, uid, context['active_id'], context=context)
        return prod.product_qty
    
    _defaults = {
                 'product_qty': _get_product_qty, 
                 'mode': lambda *x: 'consume'
                 }

    def do_move_produce(self, cr, uid, ids, context={}):
        datas = self.read(cr, uid, ids)[0]
        prod_obj = self.pool.get('mrp.production')
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(uid, 'mrp.production', context['active_id'], 'button_produce', cr)
        return {}

stock_move_produce()


class change_production_qty(osv.osv_memory):
    _name = "change.production.qty"
    _description = "Change Production Qty"
    
    _columns = {
        'product_qty': fields.float('Quantity', required=True), 
              }

    def _get_product_qty(self, cr, uid, context):
        prod = self.pool.get('mrp.production').browse(cr, uid, context['active_id'], context=context)
        return prod.product_qty
    
    _defaults = {
                 'product_qty': _get_product_qty, 
                 }

    def change_prod_qty(self, cr, uid, ids, context={}):
        datas = self.read(cr, uid, ids)[0]
        prod_obj = self.pool.get('mrp.production')
        move_lines_obj = self.pool.get('stock.move')
        new_qty = datas['product_qty']
        prod = prod_obj.browse(cr, uid, context['active_id'])
        prod_obj.write(cr, uid, prod.id, {'product_qty' :  new_qty})
        prod_obj.action_compute(cr, uid, [prod.id])
        bom_point = prod.bom_id
        bom_id = prod.bom_id.id
        if not bom_point:
            bom_id = self.pool.get('mrp.bom')._bom_find(cr, uid, prod.product_id.id, prod.product_uom.id)
            if not bom_id:
                raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))
            self.write(cr, uid, [prod.id], {'bom_id': bom_id})
            bom_point = self.pool.get('mrp.bom').browse(cr, uid, [bom_id])[0]
        factor = new_qty * prod.product_uom.factor / bom_point.product_uom.factor
        res = self.pool.get('mrp.bom')._bom_explode(cr, uid, bom_point, factor / bom_point.product_qty, [])
        qty_vals = {}
        qty_vals_done = {}
        moves = {}
        moves_done = {}
        for move in prod.move_lines:
            moves[move.product_id.id] = []
            qty_vals[move.product_id.id] = qty_vals.get(move.product_id.id, 0.0) + move.product_qty
            moves[move.product_id.id].append(move.id)
        for move in prod.move_lines2:
            moves_done[move.product_id.id] = []
            qty_vals_done[move.product_id.id] = qty_vals_done.get(move.product_id.id, 0.0) + move.product_qty
            moves_done[move.product_id.id].append(move.id)

        for r in res[0]:
            to_add = (r['product_qty'] - qty_vals_done.get(r['product_id'], 0.0)) - qty_vals.get(r['product_id'], 0.0)
            avail_qty = move_lines_obj.browse(cr, uid, moves[r['product_id']][0]).product_qty
            move_lines_obj.write(cr, uid, moves[r['product_id']][0], {'product_qty': avail_qty + to_add})
#    TODO
#        product_lines_obj = self.pool.get('mrp.production.product.line')
#        for m in prod.move_created_ids:
#            move_lines_obj.write(cr, uid,m.id, {'product_qty' :  new_qty})

        return {}
    
change_production_qty()