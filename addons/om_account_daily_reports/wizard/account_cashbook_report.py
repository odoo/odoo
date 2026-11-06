# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import date


class AccountCashBookReport(models.TransientModel):
    _name = "account.cashbook.report"
    _description = "Cash Book Report"

    def _get_default_account_ids(self):
        journals = self.env['account.journal'].search([('type', '=', 'cash')])
        accounts = []
        for journal in journals:
            if journal.default_account_id.id:
                accounts.append(journal.default_account_id.id)
            if journal.company_id.account_journal_payment_credit_account_id.id:
                accounts.append(journal.company_id.account_journal_payment_credit_account_id.id)
            if journal.company_id.account_journal_payment_debit_account_id.id:
                accounts.append(journal.company_id.account_journal_payment_debit_account_id.id)
            for acc_out in journal.outbound_payment_method_line_ids:
                if acc_out.payment_account_id:
                    accounts.append(acc_out.payment_account_id.id)
            for acc_in in journal.inbound_payment_method_line_ids:
                if acc_in.payment_account_id:
                    accounts.append(acc_in.payment_account_id.id)
        return accounts

    date_from = fields.Date(string='Start Date', default=date.today(), required=True)
    date_to = fields.Date(string='End Date', default=date.today(), required=True)
    target_move = fields.Selection([('posted', 'Posted Entries'),
                                    ('all', 'All Entries')], string='Target Moves', required=True,
                                   default='posted')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True,
                                   default=lambda self: self.env['account.journal'].search([]))
    account_ids = fields.Many2many('account.account', 'account_account_cashbook_report', 'report_line_id',
                                   'account_id', 'Accounts', default=_get_default_account_ids)

    display_account = fields.Selection(
        [('all', 'All'), ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', required=True, default='movement')
    sortby = fields.Selection(
        [('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')],
        string='Sort by',
        required=True, default='sort_date')
    initial_balance = fields.Boolean(string='Include Initial Balances',
                                     help='If you selected date, this field allow you to add a row to'
                                          ' display the amount of debit/credit/balance that precedes '
                                          'the filter you\'ve set.')

    @api.onchange('account_ids')
    def onchange_account_ids(self):
        if self.account_ids:
            journals = self.env['account.journal'].search(
                [('type', '=', 'cash')])
            accounts = []
            for journal in journals:
                accounts.append(journal.company_id.account_journal_payment_credit_account_id.id)
            domain = {'account_ids': [('id', 'in', accounts)]}
            return {'domain': domain}

    def _build_comparison_context(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form'][
            'journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form'][
            'target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read(['target_move', 'date_from', 'date_to', 'journal_ids', 'account_ids',
                                  'sortby', 'initial_balance', 'display_account'])[0]
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        return self.env.ref(
            'om_account_daily_reports.action_report_cash_book').report_action(self,
                                                                     data=data)

