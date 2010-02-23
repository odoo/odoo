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
        prod = self.pool.get('mrp.production').browse(cr, uid, 
                                context['active_id'], context=context)
        return prod.product_qty
    
    _defaults = {
                 'product_qty': _get_product_qty, 
                 'mode': lambda *x: 'consume'
                 }

    def do_move_produce(self, cr, uid, ids, context={}):
        datas = self.read(cr, uid, ids)[0]
        prod_obj = self.pool.get('mrp.production')
#        wf_service = netsvc.LocalService('workflow')
#        wf_service.trg_validate(uid, 'mrp.production', context['active_id'],
#                                 'button_produce_done', cr)
        prod_obj.action_production_end(cr, uid, [context['active_id']], 
                                qty=datas['product_qty'], mode=datas['mode'])
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
        prod_obj._change_prod_qty(cr, uid, context['active_ids'], datas['product_qty'], context=context)
        return {}
    
change_production_qty()
