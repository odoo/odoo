# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _


class stock_invoice_onshipping(osv.osv_memory):
    _inherit = "stock.invoice.onshipping"

    def _get_invoice_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        res_ids = context and context.get('active_ids', [])
        pick_obj = self.pool.get('stock.picking')
        pickings = pick_obj.browse(cr, uid, res_ids, context=context)
        pick = pickings and pickings[0]
        src_usage = pick.move_lines[0].location_id.usage
        dest_usage = pick.move_lines[0].location_dest_id.usage
        if src_usage == 'supplier' and dest_usage == 'customer':
            pick_purchase = pick.move_lines and pick.move_lines[0].purchase_line_id and pick.move_lines[0].purchase_line_id.order_id.invoice_method == 'picking'
            if pick_purchase:
                return 'in_invoice'
            else:
                return 'out_invoice'
        else:
            return super(stock_invoice_onshipping, self)._get_invoice_type(cr, uid, context=context)

    _defaults = {
        'invoice_type': _get_invoice_type,
        }
