# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_paid(self):
    	""" When an invoice linked to a sales order selling registrations is
        paid confirm attendees. Attendees should indeed not be confirmed before
        full payment. """
        res = super(AccountInvoice, self).action_invoice_paid()
        self.mapped('invoice_line_ids.sale_line_ids')._update_registrations(confirm=True)
        return res
