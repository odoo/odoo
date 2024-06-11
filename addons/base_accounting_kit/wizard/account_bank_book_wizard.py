# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BankBookWizard(models.TransientModel):
    _name = 'account.bank.book.report'
    _description = 'Account Bank Book Report'

    company_id = fields.Many2one('res.company', string='Company',
                                 readonly=True,
                                 default=lambda self: self.env.company)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')], string='Target Moves', required=True,
                                   default='posted')
    date_from = fields.Date(string='Start Date', default=date.today(),
                            required=True)
    date_to = fields.Date(string='End Date', default=date.today(),
                          required=True)
    display_account = fields.Selection(
        [('all', 'All'), ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', required=True, default='movement')
    sortby = fields.Selection(
        [('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')],
        string='Sort by',
        required=True, default='sort_date')
    initial_balance = fields.Boolean(string='Include Initial Balances',
                                     help='If you selected date, this field allow you to add a row to display the amount of debit/credit/balance that precedes the filter you\'ve set.')

    def _get_default_account_ids(self):
        journals = self.env['account.journal'].search([('type', '=', 'bank')])
        accounts = []
        for journal in journals:
            accounts.append(journal.company_id.account_journal_payment_credit_account_id.id)
        return accounts

    account_ids = fields.Many2many('account.account',
                                   'account_report_bankbook_account_rel',
                                   'report_id', 'account_id',
                                   'Accounts',
                                   default=_get_default_account_ids)
    journal_ids = fields.Many2many('account.journal',
                                   'account_report_bankbook_journal_rel',
                                   'account_id', 'journal_id',
                                   string='Journals', required=True,
                                   default=lambda self: self.env[
                                       'account.journal'].search([]))

    @api.onchange('account_ids')
    def onchange_account_ids(self):
        if self.account_ids:
            journals = self.env['account.journal'].search(
                [('type', '=', 'bank')])
            accounts = []
            for journal in journals:
                accounts.append(journal.company_id.account_journal_payment_credit_account_id.id)
            domain = {'account_ids': [('id', 'in', accounts)]}
            return {'domain': domain}

    def _build_contexts(self, data):
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
        self.ensure_one()
        if self.initial_balance and not self.date_from:
            raise UserError(_("You must choose a Start Date"))
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(
            ['date_from', 'date_to', 'journal_ids', 'target_move',
             'display_account',
             'account_ids', 'sortby', 'initial_balance'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context,
                                            lang=self.env.context.get(
                                                'lang') or 'en_US')
        return self.env.ref(
            'base_accounting_kit.action_report_bank_book').report_action(self,
                                                                         data=data)
