# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        res = super(AccountMoveLine, self).reconcile(writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
        account_move_ids = self.filtered(lambda line: line.account_id.user_type_id.type == 'payable' and line.company_id.currency_id.is_zero(line.amount_residual)).mapped("move_id").ids
        expenses = self.env['hr.expense'].search([('state', '=', 'post'), ('account_move_id', 'in', account_move_ids), ('payment_mode', '=', 'own_account')])
        expenses.paid_expenses()
        return res
