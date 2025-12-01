from odoo import fields, models, _
from datetime import date


class AccountDayBookReport(models.TransientModel):
    _name = "account.daybook.report"
    _description = "Day Book Report"

    date_from = fields.Date(string='Start Date', default=date.today(), required=True)
    date_to = fields.Date(string='End Date', default=date.today(), required=True)
    target_move = fields.Selection([('posted', 'Posted Entries'),
                                    ('all', 'All Entries')], string='Target Moves', required=True,
                                   default='posted')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True,
                                   default=lambda self: self.env['account.journal'].search([]))
    account_ids = fields.Many2many('account.account', 'account_account_daybook_report', 'report_line_id',
                                   'account_id', 'Accounts')

    def _build_comparison_context(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        result['date_from'] = data['form']['date_from']
        result['date_to'] = data['form']['date_to']
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read(['target_move', 'date_from', 'date_to', 'journal_ids', 'account_ids'])[0]
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        return self.env.ref(
            'om_account_daily_reports.action_report_day_book').report_action(self,
                                                                     data=data)




