# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

# Handle analytic account autofill in vendor bills
class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.onchange('purchase_id')
    def purchase_order_change(self):
        super(AccountInvoice, self).purchase_order_change()

        for line in self.invoice_line_ids:
            default_analytic_account = self.env['account.analytic.default'].account_get(
                line.product_id.id,
                line.purchase_id.partner_id.id,
                line.purchase_id.user_id.id,
                fields.Date.today()
            )

            if default_analytic_account:
                line.account_analytic_id = default_analytic_account.analytic_id.id
                line.analytic_tag_ids = [(6, 0, default_analytic_account.analytic_tag_ids.ids + line.analytic_tag_ids.ids)]
