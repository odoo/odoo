# -*- coding: utf-8 -*-

from openerp import fields, models


class AccountPrintJournal(models.TransientModel):
    _inherit = "account.common.journal.report"
    _name = "account.print.journal"
    _description = "Account Print Journal"

    sort_selection = fields.Selection([('date', 'Date'), ('move_name', 'Journal Entry Number'),], 'Entries Sorted by', required=True, default='move_name')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, default=lambda self: self.env['account.journal'].search([('type', 'in', ['sale', 'purchase'])]))

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection})
        return self.env['report'].with_context(landscape=True).get_action(self, 'account_extra_reports.report_journal', data=data)
