# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        res = super(AccountMoveLine, self).reconcile(writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
        account_move_ids = [l.move_id.id for l in self if l.move_id.matched_percentage == 1]
        if account_move_ids:
            expenses = self.env['hr.expense'].search([('account_move_id', 'in', account_move_ids)])
            expenses.paid_expenses()
        return res
