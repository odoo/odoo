# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.misc import frozendict


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    expense_id = fields.Many2one('hr.expense', string='Expense', copy=True) # copy=True, else we don't know price is tax incl.

    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        super(AccountMoveLine, self.filtered(lambda line: line.move_id.expense_sheet_id.payment_mode != 'company_account'))._check_payable_receivable()

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

    def _convert_to_tax_base_line_dict(self):
        result = super()._convert_to_tax_base_line_dict()
        if self.expense_id:
            result.setdefault('extra_context', {})
            result['extra_context']['force_price_include'] = True
        return result

    def _get_extra_query_base_tax_line_mapping(self):
        return ' AND (base_line.expense_id IS NULL OR account_move_line.expense_id = base_line.expense_id)'
