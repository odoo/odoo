# -*- coding: utf-8 -*-

from openerp import fields, models


class AccountBalanceReport(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = 'account.balance.report'
    _description = 'Trial Balance Report'

    journal_ids = fields.Many2many('account.journal', 'account_balance_report_journal_rel', 'account_id', 'journal_id', string='Journals', required=True, default=[])

    def _print_report(self, data):
        data = self.pre_print_report(data)
        return self.env['report'].get_action(self, 'account.report_trialbalance', data=data)
