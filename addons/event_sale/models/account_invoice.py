# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_paid(self):
        res = super(AccountInvoice, self).action_invoice_paid()
        sale_order_lines = self.mapped('invoice_line_ids').mapped('sale_line_ids')
        sale_order_lines._update_registrations(confirm=True)
        return res
