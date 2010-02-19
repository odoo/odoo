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
import re
import time
import tools

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

spilt_in_lot()

class track_lines(osv.osv_memory):
    _name = "track.lines"
    _description = "Track lines"
    
    _columns = {
        'name': fields.char('Tracking serial', size=64), 
        'lot_id': fields.many2one('spilt.in.lot', 'Lot')
              }

track_lines()
