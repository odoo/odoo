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
                accounts[line.account_id] = {'debit': 0, 'credit': 0, 'amount_currency': 0, 'lines': []}
            if self.env.context['cash_basis']:
                accounts[line.account_id]['debit'] += line.debit_cash_basis
                accounts[line.account_id]['credit'] += line.credit_cash_basis
            else:
                accounts[line.account_id]['debit'] += line.debit
                accounts[line.account_id]['credit'] += line.credit
            if line.account_id.currency_id:
                accounts[line.account_id]['amount_currency'] += line.amount_currency
            accounts[line.account_id]['lines'].append(line)
        return accounts
        
    @api.model
    def _lines(self, line_id = None):
        lines = []
        context = self.env.context
        domain = [('date', '>=', context['date_from']), ('date', '<=', context['date_to'])]
        if line_id:
            domain.append(('account_id', '=', line_id))
        if context['target_move'] == 'posted':
            domain.append(('move_id.state', '=', 'posted'))
        move_line_ids = self.env['account.move.line'].search(domain).sorted(key=lambda r: r.date)
        grouped_accounts = self.group_by_account_id(move_line_ids)
        sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
        for account in sorted_accounts:
            debit = grouped_accounts[account]['debit']
            credit = grouped_accounts[account]['credit']
            move_lines = grouped_accounts[account]['lines']
            amount_currency = '' if not account.currency_id else grouped_accounts[account]['amount_currency']
            lines.append({
                'id': account.id,
                'type': 'line',
                'name': account.code + " " + account.name,
                'footnotes': self._get_footnotes('line', account.id),
                'columns': [debit, credit, debit-credit, amount_currency],
                'colspan-name': 7,
                'level': 2,
                'unfoldable': True,
                'unfolded': account in context['context_id']['unfolded_account']
            })
            if account in context['context_id']['unfolded_account']:
                progress = 0
                for line in grouped_accounts[account]['lines']:
                    if self.env.context['cash_basis']:
                        line_debit = line.debit_cash_basis
                        line_credit = line.credit_cash_basis
                    else:
                        line_debit = line.debit
                        line_credit = line.credit
                    progress = progress + line_debit - line_credit
                    currency = "" if not line.account_id.currency_id else line.amount_currency
                    name = [line.ref] if line.ref else []
                    if line.move_id.name != "/" and line.move_id.name != line.ref:
                        name.append(line.move_id.name)
                    if line.name != "/":
                        name.append(line.name) 

                    lines.append({
                        'id': line.id,
                        'type': 'move_line_id',
                        'move_id': line.move_id.id,
                        'name': ", ".join(name),
                        'colspan-name': 3,
                        'footnotes': self._get_footnotes('move_line_id', line.id),
                        'columns': [line.date, line.journal_id.code, line.partner_id.name, line.counterpart, line_debit, line_credit, progress, currency],
                        'level': 3,
                    })
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


class account_context_general_ledger(models.TransientModel):
    _name = "account.context.general.ledger"
    _description = "A particular context for the general ledger"
    _inherit = "account.report.context.common"

    unfolded_account = fields.Many2many('account.account', 'context_to_account', string='Unfolded lines')

    def get_report_obj(self):
        return self.env['account.general.ledger']

    @api.multi
    def remove_line(self, line_id):
        self.write({'unfolded_account': [(3, line_id)]})

    @api.multi
    def add_line(self, line_id):
        self.write({'unfolded_account': [(4, line_id)]})

    def get_columns_names(self):
        columns = ["", "", _("date"), _("JRNL"), _("Partner"), _("Counterpart"), _("Debit"), _("Credit"), _("Progress"), _("Currency")]
        return columns
                                       
