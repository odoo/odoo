# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import osv
from openerp.tools.translate import _


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def do_new_transfer(self, cr, uid, ids, context=None):
        """Launch Create invoice wizard if invoice state is To be Invoiced,
          after processing the picking.
        """
        if context is None:
            context = {}
        res = super(stock_picking, self).do_new_transfer(cr, uid, ids, context=context)
        if res: #If it is already returning a wizard
            return res
        pick_ids = [p.id for p in self.browse(cr, uid, ids, context) if p.invoice_state == '2binvoiced']
        if pick_ids:
            context = dict(context, active_model='stock.picking', active_ids=pick_ids)
            return {
                'name': _('Create Invoice'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.invoice.onshipping',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
            }
        return res