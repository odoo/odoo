# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking'
    _columns = {
        'invoice_state': fields.selection([('2binvoiced', 'To be refunded/invoiced'), ('none', 'No invoicing')], 'Invoicing',required=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_return_picking, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        if pick:
            if 'invoice_state' in fields:
                if pick.invoice_state=='invoiced':
                    res.update({'invoice_state': '2binvoiced'})
                else:
                    res.update({'invoice_state': 'none'})
        return res

        

    def _create_returns(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids[0], context=context)
        new_picking, picking_type_id = super(stock_return_picking, self)._create_returns(cr, uid, ids, context=context)
        if data.invoice_state == '2binvoiced':
            pick_obj = self.pool.get("stock.picking")
            move_obj = self.pool.get("stock.move")
            move_ids = [x.id for x in pick_obj.browse(cr, uid, new_picking, context=context).move_lines]
            move_obj.write(cr, uid, move_ids, {'invoice_state': '2binvoiced'})
        return new_picking, picking_type_id
