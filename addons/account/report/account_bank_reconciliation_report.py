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


class account_bank_reconciliation_report(models.AbstractModel):
    _name = 'account.bank.reconciliation.report'
    _description = 'Bank reconciliation report'

    line_number = 0

    @api.model
    def get_lines(self, context_id, line_id=None):
        return self.with_context(
            date_from=context_id.date_from,
            journal_id=context_id.journal_id,
            context_id=context_id,
        )._lines()

    def add_title_line(self, title, amount):
        self.line_number += 1
        return {
            'id': self.line_number,
            'type': 'line',
            'name': title,
            'footnotes': self._get_footnotes('line', self.line_number),
            'columns': [self.env.context['date_from'], '', amount],
            'level': 0,
        }

    def add_subtitle_line(self, title):
        self.line_number += 1
        return {
            'id': self.line_number,
            'type': 'line',
            'name': title,
            'footnotes': self._get_footnotes('line', self.line_number),
            'columns': [self.env.context['date_from'], '', ''],
            'level': 1,
        }

    def add_total_line(self, amount):
        self.line_number += 1
        return {
            'id': self.line_number,
            'type': 'line',
            'name': '',
            'footnotes': self._get_footnotes('line', self.line_number),
            'columns': [self.env.context['date_from'], "", _("Total : ") + str(amount)],
            'level': 2,
        }

    def add_bank_statement_line(self, line, amount):
        self.line_number += 1
        return {
            'id': self.line_number,
            'statement_id': line.statement_id.id,
            'type': 'bank_statement_id',
            'name': line.name,
            'footnotes': self._get_footnotes('bank_statement_id', self.line_number),
            'columns': [line.date, line.ref, amount],
            'level': 3,
        }

    @api.model
    def _lines(self):
        lines = []
        #Start amount
        account_ids = list(set([self.env.context['journal_id'].default_debit_account_id.id, self.env.context['journal_id'].default_credit_account_id.id]))
        lines_already_accounted = self.env['account.move.line'].search([('account_id', 'in', account_ids),
                                                                        ('date', '<=', self.env.context['date_from'])])
        start_amount = sum([line.balance for line in lines_already_accounted])
        lines.append(self.add_title_line(_("Balance in Odoo"), start_amount))

        # Outstanding plus
        not_reconcile_plus = self.env['account.bank.statement.line'].search([('statement_id.journal_id', '=', self.env.context['journal_id'].id),
                                                                             ('date', '<=', self.env.context['date_from']),
                                                                             ('journal_entry_ids', '=', False),
                                                                             ('amount', '>', 0)])
        outstanding_plus_tot = 0
        if not_reconcile_plus:
            lines.append(self.add_subtitle_line(_("Plus Outstanding Payment")))
            for line in not_reconcile_plus:
                lines.append(self.add_bank_statement_line(line, line.amount))
                outstanding_plus_tot += line.amount
            lines.append(self.add_total_line(outstanding_plus_tot))

        # Outstanding less
        not_reconcile_less = self.env['account.bank.statement.line'].search([('statement_id.journal_id', '=', self.env.context['journal_id'].id),
                                                                             ('date', '<=', self.env.context['date_from']),
                                                                             ('journal_entry_ids', '=', False),
                                                                             ('amount', '<', 0)])
        outstanding_less_tot = 0
        if not_reconcile_less:
            lines.append(self.add_subtitle_line(_("Less Outstanding Receipt")))
            for line in not_reconcile_less:
                lines.append(self.add_bank_statement_line(line, line.amount))
                outstanding_less_tot += line.amount
            lines.append(self.add_total_line(outstanding_less_tot))

        # Un-reconcilied bank statement lines
        move_lines = self.env['account.move.line'].search([('move_id.journal_id', '=', self.env.context['journal_id'].id),
                                                           ('move_id.statement_line_id', '=', False),
                                                           ('user_type.type', '!=', 'liquidity'),
                                                           ('date', '<=', self.env.context['date_from'])])
        unrec_tot = 0
        if move_lines:
            lines.append(self.add_subtitle_line(_("Plus Un-Reconciled Bank Statement Lines")))
            for line in move_lines:
                self.line_number += 1
                lines.append({
                    'id': self.line_number,
                    'move_id': line.move_id.id,
                    'type': 'move_line_id',
                    'name': line.name,
                    'footnotes': self._get_footnotes('move_line_id', self.line_number),
                    'columns': [line.date, line.ref, line.balance],
                    'level': 3,
                })
                unrec_tot += line.balance
            lines.append(self.add_total_line(unrec_tot))

        # Final
        lines.append(self.add_title_line(_("Statement Balance"), start_amount + outstanding_plus_tot + outstanding_less_tot + unrec_tot))
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
        return _("Bank Reconciliation")

    @api.model
    def get_name(self):
        return 'bank_reconciliation'

    @api.model
    def get_report_type(self):
        return 'bank_reconciliation'


class account_report_context_bank_reconciliation(models.TransientModel):
    _name = 'account.report.context.bank.reconciliation'
    _description = 'A particular context for the bank reconciliation report'
    _inherit = 'account.report.context.common'

    def _get_bank_journals(self):
        self.journals = self.env['account.journal'].search([['type', '=', 'bank']])

    journal_id = fields.Many2one('account.journal', string=_("Bank account"))
    journals = fields.One2many('account.journal', string=_("Bank Accounts"), compute=_get_bank_journals)

    def get_report_obj(self):
        return self.env['account.bank.reconciliation.report']

    def get_columns_names(self):
        columns = [_("Date"), _("Reference"), _("Amount")]
        return columns
