# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.misc import frozendict


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    expense_id = fields.Many2one('hr.expense', string='Expense', copy=False)

    def reconcile(self):
        # OVERRIDE
        not_paid_expenses = self.expense_id.filtered(lambda expense: expense.state != 'done')
        res = super().reconcile()
        # Do not update expense or expense sheet states when reversing journal entries
        not_paid_expense_sheets = not_paid_expenses.sheet_id.filtered(lambda sheet: sheet.account_move_id.payment_state != 'reversed')
        paid_expenses = not_paid_expenses.filtered(lambda expense: expense.currency_id.is_zero(expense.amount_residual))
        paid_expenses.write({'state': 'done'})
        not_paid_expense_sheets.filtered(lambda sheet: all(expense.state == 'done' for expense in sheet.expense_line_ids)).set_to_paid()
        return res

    def _get_attachment_domains(self):
        attachment_domains = super(AccountMoveLine, self)._get_attachment_domains()
        if self.expense_id:
            attachment_domains.append([('res_model', '=', 'hr.expense'), ('res_id', '=', self.expense_id.id)])
        return attachment_domains

    def _compute_tax_key(self):
        super()._compute_tax_key()
        for line in self:
            if line.expense_id:
                line.tax_key = frozendict(**line.tax_key, expense_id=line.expense_id.id)

    def _compute_all_tax(self):
        expense_lines = self.filtered('expense_id')
        super(AccountMoveLine, expense_lines.with_context(force_price_include=True))._compute_all_tax()
        super(AccountMoveLine, self - expense_lines)._compute_all_tax()
        for line in expense_lines:
            for key in list(line.compute_all_tax.keys()):
                new_key = frozendict(**key, expense_id=line.expense_id.id)
                line.compute_all_tax[new_key] = line.compute_all_tax.pop(key)

    def _compute_totals(self):
        expenses = self.filtered('expense_id')
        super(AccountMoveLine, expenses.with_context(force_price_include=True))._compute_totals()
        super(AccountMoveLine, self - expenses)._compute_totals()

    def _compute_term_key(self):
        super()._compute_term_key()
        for line in self:
            if line.expense_id:
                line.term_key = line.term_key and frozendict(**line.term_key, expense_id=line.expense_id.id)

    def _convert_to_tax_base_line_dict(self):
        result = super()._convert_to_tax_base_line_dict()
        if self.move_id.expense_sheet_id:
            result.setdefault('extra_context', {})
            result['extra_context']['force_price_include'] = True
        return result
