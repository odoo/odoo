# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import UserError


class AccountInvoiceConfirm(models.TransientModel):
    """
    This wizard will confirm the all the selected draft invoices
    """

    _name = "account.invoice.confirm"
    _description = "Confirm the selected invoices"

    @api.multi
    def invoice_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        invoice_list = self.env['account.invoice'].browse(active_ids).sorted(lambda i: (i.date_invoice or fields.Date.context_today(self), i.reference or '', i.id))
        for record in invoice_list:
            if record.state != 'draft':
                raise UserError(_("Selected invoice(s) cannot be confirmed as they are not in 'Draft' state."))
            record.action_invoice_open()
        return {'type': 'ir.actions.act_window_close'}
