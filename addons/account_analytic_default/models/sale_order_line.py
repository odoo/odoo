# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp.osv import osv
from openerp import api


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(sale_order_line, self)._prepare_invoice_line(qty)
        default_analytic_account = self.env['account.analytic.default'].account_get(self.product_id.id, self.order_id.partner_id.id, self.order_id.user_id.id, time.strftime('%Y-%m-%d'))
        if default_analytic_account:
            res.update({'account_analytic_id': default_analytic_account.analytic_id.id})
        return res
