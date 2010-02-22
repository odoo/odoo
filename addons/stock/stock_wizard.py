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

class stock_move_track(osv.osv_memory):
    _name = "stock.move.track"
    _description = "Track moves"
    
    _columns = {
        'tracking_prefix': fields.char('Tracking prefix', size=64), 
        'quantity': fields.float("Quantity per lot")
              }

    _defaults = {
        'quantity': lambda *x: 1
                 }
    
    def track_lines(self, cr, uid, ids, context={}):
        datas = self.read(cr, uid, ids)[0]
        move_obj = self.pool.get('stock.move')
        move_obj._track_lines(cr, uid, context['active_id'], datas, context=context)
        return {}

stock_move_track()

class stock_move_consume(osv.osv_memory):
    _name = "stock.move.consume"
    _description = "Consume Products"
    
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True), 
        'product_qty': fields.float('Quantity', required=True), 
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True), 
        'location_id': fields.many2one('stock.location', 'Source Location', required=True)
              }

    def _get_product_id(self, cr, uid, context):
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        return move.product_id.id
    
    def _get_product_qty(self, cr, uid, context):
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        return move.product_qty
    
    def _get_product_uom(self, cr, uid, context):
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        return move.product_uom.id
    
    def _get_location_id(self, cr, uid, context):
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        return move.location_id.id
    
    _defaults = {
                 'product_id': _get_product_id, 
                 'product_qty': _get_product_qty, 
                 'product_uom': _get_product_uom, 
                 'location_id': _get_location_id
                 }

    def do_move_consume(self, cr, uid, ids, context={}):
        datas = self.read(cr, uid, ids)[0]
        move_obj = self.pool.get('stock.move')
        move_obj.consume_moves(cr, uid, context['active_id'], 
                         datas['product_qty'], datas['location_id'], 
                         context=context)
        return {}

stock_move_consume()


class stock_move_scrap(osv.osv_memory):
    _name = "stock.move.scrap"
    _description = "Scrap Products"
    _inherit = "stock.move.consume"
    
    _defaults = {
                 'location_id': lambda *x: False
                 }

    def move_scrap(self, cr, uid, ids, context={}):
        datas = self.read(cr, uid, ids)[0]
        move_obj = self.pool.get('stock.move')
        move_obj.scrap_moves(cr, uid, context['active_id'], 
                         datas['product_qty'], datas['location_id'], 
                         context=context)
        return {}

stock_move_scrap()


class spilt_in_lot(osv.osv_memory):
    _name = "spilt.in.lot"
    _description = "Split in lots"
    
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'line_ids': fields.one2many('track.lines', 'lot_id', 'Lots Number')
              }
    
    def _get_product_id(self, cr, uid, context):
        move = self.pool.get('stock.move').browse(cr, uid, context['active_id'], context=context)
        return move.product_id.id
    
    _defaults = {
                 'product_id': _get_product_id, 
                 }
    
    def split_lot(self, cr, uid, ids, context=None):
        datas = self.read(cr, uid, ids)[0]
        lines = []
        for line in self.pool.get('track.lines').browse(cr, uid, datas.get('line_ids', [])):
            lines.append({'tracking_num': line.name, 'quantity': line.quantity})
        move_obj = self.pool.get('stock.move')
        move_obj._track_lines(cr, uid, context['active_id'], lines, context=context)
        return {}

spilt_in_lot()

class track_lines(osv.osv_memory):
    _name = "track.lines"
    _description = "Track lines"
    
    _columns = {
        'name': fields.char('Tracking serial', size=64), 
        'quantity': fields.integer('Quantity'), 
        'lot_id': fields.many2one('spilt.in.lot', 'Lot')
              }

track_lines()
