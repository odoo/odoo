# -*- coding: utf-8 -*-

from openerp import models, fields, api

import werkzeug.urls

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    paypal_url = fields.Char('Paypal Url', compute='_compute_paypal_url')

    @api.depends('type', 'number', 'company_id', 'currency_id')
    def _compute_paypal_url(self):
        for inv in self:
            if inv.type == 'out_invoice' and inv.company_id.paypal_account:
                params = {
                    "cmd": "_xclick",
                    "business": inv.company_id.paypal_account,
                    "item_name": "%s Invoice %s" % (inv.company_id.name, inv.number or ''),
                    "invoice": inv.number,
                    "amount": inv.residual,
                    "currency_code": inv.currency_id.name,
                    "button_subtype": "services",
                    "no_note": "1",
                    "bn": "Odoo_Invoice_PayNow_" + inv.currency_id.name,
                }
                inv.paypal_url = "https://www.paypal.com/cgi-bin/webscr?" + werkzeug.url_encode(params)
