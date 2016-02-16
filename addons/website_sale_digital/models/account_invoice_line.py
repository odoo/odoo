# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class AccountInvoiceLine(models.Model):
    _inherit = ['account.invoice.line']

    def get_digital_purchases(self):
        # Get paid invoices
        purchases = self.sudo().search([('invoice_id.state', '=', 'paid'), ('invoice_id.partner_id', '=', self.env.user.partner_id.id), ('product_id.product_tmpl_id.type', '=', 'digital')])

        return purchases.mapped('product_id')
