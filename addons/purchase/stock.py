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
from openerp import netsvc
class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'purchase_line_id': fields.many2one('purchase.order.line',
            'Purchase Order Line', ondelete='set null', select=True,
            readonly=True),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        from openerp import workflow
        for id in ids:
            workflow.trg_trigger(uid, 'stock.move', id, cr)
        return res

class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _get_to_invoice(self, cr, uid, ids, name, args, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            for move in picking.move_lines:
                if move.purchase_line_id and move.purchase_line_id.order_id.invoice_method == 'picking':
                    if not move.move_orig_ids:
                        res[picking.id] = True
        return res

    def _get_picking_to_recompute(self, cr, uid, ids, context=None):
        picking_ids = set()
        for move in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            if move.picking_id:
                picking_ids.add(move.picking_id.id)
        return list(picking_ids)

    _columns = {
        'reception_to_invoice': fields.function(_get_to_invoice, type='boolean', string='Invoiceable on incoming shipment?',
               help='Does the picking contains some moves related to a purchase order invoiceable on the reception?',
               store={
                   'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 10),
                   'stock.move': (_get_picking_to_recompute, ['purchase_line_id', 'picking_id'], 10),
               }),
    }


    # TODO: Invoice based on receptions
    # Here is how it should work:
    #   On a draft invoice, allows to select purchase_orders (many2many_tags)
    # This fills in automatically PO lines or from related receptions if any
