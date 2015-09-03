# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)


class stock_inventory(osv.osv):
    _inherit = "stock.inventory"
    _columns = {
        'accounting_date': fields.date('Force Accounting Date', help="Choose the accounting date at which you want to value the stock moves created by the inventory instead of the default one (the inventory end date)"),
    }

    def post_inventory(self, cr, uid, inv, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        if inv.accounting_date:
            ctx['force_period_date'] = inv.accounting_date
        return super(stock_inventory, self).post_inventory(cr, uid, inv, context=ctx)
