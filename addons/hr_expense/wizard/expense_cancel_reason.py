# -*- coding: utf-8 -*-

from openerp import models, fields, api


class ExpenseCancelReason(models.TransientModel):

    _name = "expense.cancel.resson"
    _description = "Expense Cancel Reason"

    description = fields.Char(string='Reason', required=True)

    @api.multi
    def expense_cancel_reason(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense = self.env['hr.expense'].browse(active_ids)
        expense.note = self.description
        expense.cancel_expenses()
        return {'type': 'ir.actions.act_window_close'}
