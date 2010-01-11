# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
import time
import netsvc

class stock_move(osv.osv):
    _inherit = 'stock.move'
    
    _columns = {
        'pos_line_id': fields.many2one('pos.order.line',
            'Pos Order Line', ondelete='set null', select=True,
            readonly=True),
    }
    
stock_move()


class stock_picking(osv.osv):

    _inherit = 'stock.picking'
    _columns = {
        'pos_order': fields.many2one('pos.order', 'Pos order'),
    }
    
    def _get_discount_invoice(self, cursor, user, move_line):
        if move_line.pos_line_id:
           return move_line.pos_line_id.discount
        return super(stock_picking, self)._get_discount_invoice(cursor, user,
               move_line)

stock_picking()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

