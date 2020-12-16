# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_invoice_paid(self):
        # OVERRIDE to mark as paid the expense sheets.
        res = super().action_invoice_paid()

        if self:
            expense_sheets = self.env['hr.expense.sheet'].search([
                ('account_move_id', 'in', self.ids),
                ('state', '!=', 'done'),
            ])
            expense_sheets.set_to_paid()

        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    expense_id = fields.Many2one('hr.expense', string='Expense', copy=False, help="Expense where the move line come from")

    def _get_attachment_domains(self):
        attachment_domains = super(AccountMoveLine, self)._get_attachment_domains()
        if self.expense_id:
            attachment_domains.append([('res_model', '=', 'hr.expense'), ('res_id', '=', self.expense_id.id)])
        return attachment_domains
