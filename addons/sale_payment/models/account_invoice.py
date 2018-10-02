# -*- coding: utf-8 -*-
from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_open(self):
        # OVERRIDE
        # Auto-reconcile the invoice with payments coming from transactions.
        # It's useful when you have a "paid" sale order (using a payment transaction) and you invoice it later.
        res = super(AccountInvoice, self).action_invoice_open()

        if not self:
            return res

        for invoice in self:
            payments = invoice.mapped('transaction_ids.payment_id')
            move_lines = payments.mapped('move_line_ids').filtered(lambda line: not line.reconciled and line.credit > 0.0)
            for line in move_lines:
                invoice.assign_outstanding_credit(line.id)
        return res
