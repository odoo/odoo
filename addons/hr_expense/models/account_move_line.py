# -*- coding: utf-8 -*-

from openerp import api, models

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def reconcile(self, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        res = super(AccountMoveLine, self).reconcile(type=type, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
        #when making a full reconciliation of account move lines 'ids', we may need to recompute the state of some hr.expense
        account_move_ids = self.filtered(lambda line: line.account_id.type == 'payable' and line.company_id.currency_id.is_zero(line.amount_residual)).mapped("move_id").ids
        expenses = self.env['hr.expense.sheet'].search([('state', '=', 'done'), ('account_move_id', 'in', account_move_ids)])
        expenses.write({'state': 'paid'})
        expenses.line_ids.filtered(lambda expense: expense.state != 'cancel').write({'state': 'paid'})
        return res
