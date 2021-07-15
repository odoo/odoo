# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    expense_id = fields.Many2one('hr.expense', string='Expense', copy=False, help="Expense where the move line come from")

    def reconcile(self):
        # OVERRIDE
        not_paid_expenses = self.expense_id.filtered(lambda expense: expense.state != 'done')
        not_paid_expense_sheets = not_paid_expenses.sheet_id
        res = super().reconcile()
        paid_expenses = not_paid_expenses.filtered(lambda expense: expense.currency_id.is_zero(expense.amount_residual))
        paid_expenses.write({'state': 'done'})
        not_paid_expense_sheets.filtered(lambda sheet: all(expense.state == 'done' for expense in sheet.expense_line_ids)).set_to_paid()
        return res

    def _get_attachment_domains(self):
        attachment_domains = super(AccountMoveLine, self)._get_attachment_domains()
        if self.expense_id:
            attachment_domains.append([('res_model', '=', 'hr.expense'), ('res_id', '=', self.expense_id.id)])
        return attachment_domains
