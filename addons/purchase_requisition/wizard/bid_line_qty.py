# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

class bid_line_qty(osv.osv_memory):
    _name = "bid.line.qty"
    _description = "Change Bid line quantity"
    _columns = {
        'qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
    }

    def change_qty(self, cr, uid, ids, context=None):
        active_ids = context and context.get('active_ids', [])
        data = self.browse(cr, uid, ids, context=context)[0]
        self.pool.get('purchase.order.line').write(cr, uid, active_ids, {'quantity_tendered': data.qty})
        return {'type': 'ir.actions.act_window_close'}
