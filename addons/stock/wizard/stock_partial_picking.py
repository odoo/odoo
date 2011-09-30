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

import time
from osv import fields, osv
from tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

class stock_partial_picking_line(osv.TransientModel):
    _name = "stock.partial.picking.line"
    _rec_name = 'product_id'
    _columns = {
        'product_id' : fields.many2one('product.product', string="Product", required=True, ondelete='CASCADE'),
        'quantity' : fields.float("Quantity", required=True),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True, ondelete='CASCADE'),
        'prodlot_id' : fields.many2one('stock.production.lot', 'Production Lot', ondelete='CASCADE'),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete='CASCADE'),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', required=True, ondelete='CASCADE'),
        'move_id' : fields.many2one('stock.move', "Move", ondelete='CASCADE'),
        'wizard_id' : fields.many2one('stock.partial.picking', string="Wizard", ondelete='CASCADE'),
        'update_cost': fields.boolean('Need cost update'),
        'cost' : fields.float("Cost", help="Unit Cost for this product line"),
        'currency' : fields.many2one('res.currency', string="Currency", help="Currency in which Unit cost is expressed", ondelete='CASCADE'),
    }

class stock_partial_picking(osv.osv_memory):
    _name = "stock.partial.picking"
    _description = "Partial Picking Processing Wizard"
    _columns = {
        'date': fields.datetime('Date', required=True),
        'move_ids' : fields.one2many('stock.partial.picking.line', 'wizard_id', 'Product Moves'),
        'picking_id': fields.many2one('stock.picking', 'Picking', required=True, ondelete='CASCADE'),
     }

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(stock_partial_picking, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        if not picking_ids or (not context.get('active_model') == 'stock.picking') \
            or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        picking_id, = picking_ids
        if 'picking_id' in fields:
            res.update(picking_id=picking_id)
        if 'move_ids' in fields:
            picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
            moves = [self._partial_move_for(cr, uid, m) for m in picking.move_lines if m.state not in ('done','cancel')]
            res.update(move_ids=moves)
        if 'date' in fields:
            res.update(date=time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        return res

    def _product_cost_for_average_update(self, cr, uid, move):
        """Returns product cost and currency ID for the given move, suited for re-computing
           the average product cost.
        
           :return: map of the form::

                {'cost': 123.34,
                 'currency': 42}
        """
        # Currently, the cost on the product form is supposed to be expressed in the currency
        # of the company owning the product. If not set, we fall back to the picking's company,
        # which should work in simple cases.
        return {'cost': move.product_id.standard_price,
                'currency': move.product_id.company_id.currency_id.id \
                                or move.picking_id.company_id.currency_id.id \
                                or False}

    def _partial_move_for(self, cr, uid, move):
        partial_move = {
            'product_id' : move.product_id.id,
            'quantity' : move.product_qty,
            'product_uom' : move.product_uom.id,
            'prodlot_id' : move.prodlot_id.id,
            'move_id' : move.id,
            'location_id' : move.location_id.id,
            'location_dest_id' : move.location_dest_id.id,
        }
        if move.picking_id.type == 'in' and move.product_id.cost_method == 'average':
            partial_move.update(update_cost=True, **self._product_cost_for_average_update(cr, uid, move))
        return partial_move

    def do_partial(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'Partial picking processing may only be done one at a time'
        stock_picking = self.pool.get('stock.picking')
        stock_move = self.pool.get('stock.move')
        partial = self.browse(cr, uid, ids[0], context=context)
        partial_data = {
            'delivery_date' : partial.date
        }
        picking_type = partial.picking_id.type
        for move in partial.move_ids:
            move_id = move.move_id.id
            if not move_id:
                seq_obj_name =  'stock.picking.' + picking_type
                move_id = stock_move.create(cr,uid,{'name' : self.pool.get('ir.sequence').get(cr, uid, seq_obj_name),
                                                    'product_id': move.product_id.id,
                                                    'product_qty': move.quantity,
                                                    'product_uom': move.product_uom.id,
                                                    'prodlot_id': move.prodlot_id.id,
                                                    'location_id' : move.location_id.id,
                                                    'location_dest_id' : move.location_dest_id.id,
                                                    'picking_id': partial.picking_id.id
                                                    },context=context)
                stock_move.action_done(cr, uid, [move_id], context)
            partial_data['move%s' % (move_id)] = {
                'product_id': move.product_id.id,
                'product_qty': move.quantity,
                'product_uom': move.product_uom.id,
                'prodlot_id': move.prodlot_id.id,
            }
            if (picking_type == 'in') and (move.product_id.cost_method == 'average'):
                partial_data['move%s' % (move.move_id.id)].update(product_price=move.cost,
                                                                  product_currency=move.currency.id)
        stock_picking.do_partial(cr, uid, [partial.picking_id.id], partial_data, context=context)
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: