# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenErp S.A. (<http://odoo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.tools.misc import formatLang
from datetime import datetime


class report_account_general_ledger(models.AbstractModel):
    _name = "account.general.ledger"
    _description = "General Ledger Report"

    @api.model
    def get_lines(self, context_id, line_id=None):
        if type(context_id) == int:
            context_id = self.env['account.context.general.ledger'].search([['id', '=', context_id]])
        new_context = dict(self.env.context)
        new_context.update({
            'date_from': context_id.date_from,
            'date_to': context_id.date_to,
            'target_move': context_id.all_entries and 'all' or 'posted',
            'cash_basis': context_id.cash_basis,
            'context_id': context_id,
        })
        return self.with_context(new_context)._lines(line_id)

    def group_by_account_id(self, lines):
        accounts = {}
        for line in lines:
            if line.account_id not in accounts:
                accounts[line.account_id] = {'lines': []}
            accounts[line.account_id]['lines'].append(line)
        select = ',COALESCE(SUM(\"account_move_line\".debit-\"account_move_line\".credit), 0),SUM(\"account_move_line\".amount_currency),SUM(\"account_move_line\".debit),SUM(\"account_move_line\".credit)'
        if self.env.context.get('cash_basis'):
            select = select.replace('debit', 'debit_cash_basis').replace('credit', 'credit_cash_basis')
        sql = "SELECT \"account_move_line\".account_id%s FROM \"account_move_line\" WHERE %s GROUP BY \"account_move_line\".account_id"
        where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (select, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        results = dict([(k[0], {'balance': k[1], 'amount_currency': k[2], 'debit': k[3], 'credit': k[4]}) for k in results])
        for account_id, result in results.items():
            account = self.env['account.account'].browse(account_id)
            if account in accounts:
                accounts[account].update(result)
        return accounts

    @api.model
    def _lines(self, line_id=None):
        currency_id = self.env.user.company_id.currency_id
        lines = []
        context = self.env.context
        domain = [('date', '>=', context['date_from']), ('date', '<=', context['date_to'])]
        if line_id:
            domain.append(('account_id', '=', line_id))
        if context['target_move'] == 'posted':
            domain.append(('move_id.state', '=', 'posted'))
        move_line_ids = self.env['account.move.line'].search(domain)
        company_id = context.get('company_id') or self.env.user.company_id
        grouped_accounts = self.with_context({'date_from': company_id.compute_fiscalyear_dates(datetime.strptime(context['date_from'], "%Y-%m-%d"))['date_from']}).group_by_account_id(move_line_ids)
        sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
        for account in sorted_accounts:
            debit = grouped_accounts[account]['debit']
            credit = grouped_accounts[account]['credit']
            balance = grouped_accounts[account]['balance']
            amount_currency = '' if not account.currency_id else grouped_accounts[account]['amount_currency']
            lines.append({
                'id': account.id,
                'type': 'line',
                'name': account.code + " " + account.name,
                'footnotes': self._get_footnotes('line', account.id),
                'columns': ['', '', '', amount_currency, formatLang(self.env, debit, currency_obj=currency_id), formatLang(self.env, credit, currency_obj=currency_id), formatLang(self.env, balance, currency_obj=currency_id)],
                'level': 2,
                'unfoldable': True,
                'unfolded': account in context['context_id']['unfolded_accounts'],
                'colspan': 4,
            })
            initial_currency = amount_currency
            initial_debit = debit
            initial_credit = credit
            initial_balance = balance
            if account in context['context_id']['unfolded_accounts']:
                progress = 0
                domain_lines = []
                amls = grouped_accounts[account]['lines']
                too_many = False
                if len(amls) > 80 and not context.get('print_mode'):
                    amls = amls[-80:]
                    too_many = True
                for line in amls:
                    if self.env.context['cash_basis']:
                        line_debit = line.debit_cash_basis
                        line_credit = line.credit_cash_basis
                    else:
                        line_debit = line.debit
                        line_credit = line.credit
                    progress = progress + line_debit - line_credit
                    currency = "" if not line.account_id.currency_id else line.amount_currency
                    name = []
                    name = line.name and line.name or '/'
                    if len(name) > 35:
                        name = name[:32] + "..."
                    domain_lines.append({
                        'id': line.id,
                        'type': 'move_line_id',
                        'move_id': line.move_id.id,
                        'action': line.get_model_id_and_name(),
                        'name': line.move_id.name if line.move_id.name else '/',
                        'footnotes': self._get_footnotes('move_line_id', line.id),
                        'columns': [line.date, name, line.partner_id.name, currency, formatLang(self.env, line_debit, currency_obj=currency_id), formatLang(self.env, line_credit, currency_obj=currency_id), formatLang(self.env, progress, currency_obj=currency_id)],
                        'level': 1,
                    })
                    if currency and initial_currency:
                        initial_currency -= currency
                    initial_debit -= line_debit
                    initial_credit -= line_credit
                initial_balance -= progress
                domain_lines[:0] = [{
                    'id': account.id,
                    'type': 'initial_balance',
                    'name': 'Initial Balance',
                    'footnotes': self._get_footnotes('initial_balance', account.id),
                    'columns': ['', '', '', initial_currency, formatLang(self.env, initial_debit, currency_obj=currency_id), formatLang(self.env, initial_credit, currency_obj=currency_id), formatLang(self.env, initial_balance, currency_obj=currency_id)],
                    'level': 1,
                }]
                if too_many:
                    domain_lines.append({
                        'id': account.id,
                        'type': 'too_many',
                        'name': 'There are more than 80 items in this list, click here to see all of them',
                        'footnotes': [],
                        'colspan': 8,
                        'columns': [],
                        'level': 3,
                    })
                lines += domain_lines
        return lines

    @api.model
    def _get_footnotes(self, type, target_id):
        footnotes = self.env.context['context_id'].footnotes.filtered(lambda s: s.type == type and s.target_id == target_id)
        result = {}
        for footnote in footnotes:
            result.update({footnote.column: footnote.number})
        return result

    @api.model
    def get_title(self):
        return _("General Ledger")

    @api.model
    def get_name(self):
        return 'general_ledger'

    @api.model
    def get_report_type(self):
        return 'no_comparison'

    def get_template(self):
        return 'account_reports.report_financial'


class account_context_general_ledger(models.TransientModel):
    _name = "account.context.general.ledger"
    _description = "A particular context for the general ledger"
    _inherit = "account.report.context.common"

    unfolded_accounts = fields.Many2many('account.account', 'context_to_account', string='Unfolded lines')

    def get_report_obj(self):
        return self.env['account.general.ledger']

    @api.multi
    def remove_line(self, line_id):
        self.write({'unfolded_accounts': [(3, line_id)]})

    @api.multi
    def add_line(self, line_id):
        self.write({'unfolded_accounts': [(4, line_id)]})

    def get_columns_names(self):
        return [_("Date"), _("Communication"), _("Partner"), _("Currency"), _("Debit"), _("Credit"), _("Balance")]

    @api.multi
    def get_columns_types(self):
        return ["date", "text", "text", "number", "number", "number", "number"]
