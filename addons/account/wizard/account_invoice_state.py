# -*- coding: utf-8 -*-
from openerp import models, api, _
from openerp.exceptions import UserError


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

        for record in self.env['account.invoice'].browse(active_ids):
            if record.state not in ('draft', 'proforma', 'proforma2'):
                raise UserError(_("Selected invoice(s) cannot be confirmed as they are not in 'Draft' or 'Pro-Forma' state."))
            record.signal_workflow('invoice_open')
        return {'type': 'ir.actions.act_window_close'}


class AccountInvoiceCancel(models.TransientModel):
    """
    This wizard will cancel the all the selected invoices.
    If in the journal, the option allow cancelling entry is not selected then it will give warning message.
    """

    _name = "account.invoice.cancel"
    _description = "Cancel the Selected Invoices"

    @api.multi
    def invoice_cancel(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['account.invoice'].browse(active_ids):
            if record.state in ('cancel', 'paid'):
                raise UserError(_("Selected invoice(s) cannot be cancelled as they are already in 'Cancelled' or 'Done' state."))
            record.signal_workflow('invoice_cancel')
        return {'type': 'ir.actions.act_window_close'}
