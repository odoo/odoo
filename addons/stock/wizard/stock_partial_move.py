# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP SA (<http://openerp.com>).
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
from tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import time

class stock_partial_move_line(osv.osv_memory):
    _inherit = "stock.partial.picking.line"
    _name = "stock.partial.move.line"
    _columns = {
        'wizard_id' : fields.many2one('stock.partial.move', string="Wizard", ondelete='CASCADE'),
    }

class stock_partial_move(osv.osv_memory):
    _name = "stock.partial.move"
    _inherit = 'stock.partial.picking'
    _description = "Partial Move Processing Wizard"
    _columns = {
        'date': fields.datetime('Date', required=True),
        'move_ids' : fields.one2many('stock.partial.move.line', 'wizard_id', 'Moves'),

        # picking_id is not used for move processing, so we remove the required attribute
        # from the inherited column, and ignore it
        'picking_id': fields.many2one('stock.picking', 'Picking'),
     }

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        # no call to super!
        res = {}
        move_ids = context.get('active_ids', [])
        if not move_ids or not context.get('active_model') == 'stock.move':
            return res
        if 'move_ids' in fields:
            move_ids = self.pool.get('stock.move').browse(cr, uid, move_ids, context=context)
            moves = [self._partial_move_for(cr, uid, m) for m in move_ids if m.state not in ('done','cancel')]
            res.update(move_ids=moves)
        if 'date' in fields:
            res.update(date=time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        return res

    def do_partial(self, cr, uid, ids, context=None):
        # no call to super!
        assert len(ids) == 1, 'Partial move processing may only be done one form at a time.'
        partial = self.browse(cr, uid, ids[0], context=context)
        partial_data = {
            'delivery_date' : partial.date
        }
        moves_ids = []
        for move in partial.move_ids:
            move_id = move.move_id.id
            partial_data['move%s' % (move_id)] = {
                'product_id': move.product_id.id,
                'product_qty': move.quantity,
                'product_uom': move.product_uom.id,
                'prodlot_id': move.prodlot_id.id,
            }
            moves_ids.append(move_id)
            if (move.move_id.picking_id.type == 'in') and (move.product_id.cost_method == 'average'):
                partial_data['move%s' % (move_id)].update(product_price=move.cost,
                                                          product_currency=move.currency.id)
        self.pool.get('stock.move').do_partial(cr, uid, moves_ids, partial_data, context=context)
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
