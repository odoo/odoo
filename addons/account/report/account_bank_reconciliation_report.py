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


class account_bank_reconciliation(models.AbstractModel):
    _name = 'account.bank.reconciliation'
    _description = 'Bank reconciliation report'

    @api.model
    def get_lines(self, context_id, line_id=None):
        return self.with_context(
            date_from=context_id.date_from,
            journal_id=context_id.journal_id,
            context_id=context_id,
        )._lines()

    def add_title_line(self, lines, line_id, title, amount):
        lines.append({
            'id': line_id,
            'type': 'line',
            'name': title,
            'footnotes': self._get_footnotes('line', line_id),
            'columns': [self.env.context['date_from'], '', amount],
            'level': 0,
        })
        return line_id + 1

    def add_subtitle_line(self, lines, line_id, title):
        lines.append({
            'id': line_id,
            'type': 'line',
            'name': title,
            'footnotes': self._get_footnotes('line', line_id),
            'columns': [self.env.context['date_from'], '', ''],
            'level': 1,
        })
        return line_id + 1

    def add_total_line(self, lines, line_id, amount):
        lines.append({
            'id': line_id,
            'type': 'line',
            'name': '',
            'footnotes': self._get_footnotes('line', line_id),
            'columns': [self.env.context['date_from'], "", _("Total : ") + str(amount)],
            'level': 2,
        })
        return line_id + 1
        
    def add_bank_statement_line(self, lines, line, amount):
        lines.append({
            'id': line.id,
            'statement_id': line.statement_id.id,
            'type': 'bank_statement_id',
            'name': line.name,
            'footnotes': self._get_footnotes('bank_statement_id', line.id),
            'columns': [line.date, line.ref, amount],
            'level': 3,
        })

    @api.model
    def _lines(self):
        lines = []
        line_id = 1
        #Start amount
        reconcile_lines = self.env['account.bank.statement.line'].search([['statement_id.journal_id', '=', self.env.context['journal_id'].id],
                                                                     ['date', '<=', self.env.context['date_from']],
                                                                     ['journal_entry_ids', '!=', False]])
        start_amount = sum([line.amount for line in reconcile_lines])
        line_id = self.add_title_line(lines, line_id, _("Initial balance"), start_amount)

        #Outstanding
        not_reconcile_plus = self.env['account.bank.statement.line'].search([['statement_id.journal_id', '=', self.env.context['journal_id'].id],
                                                                             ['date', '<=', self.env.context['date_from']],
                                                                             ['journal_entry_ids', '=', False],
                                                                             ['amount', '>=', 0]])
        # Outstanding plus
        outstanding_plus_tot = 0
        if len(not_reconcile_plus) > 0:
            line_id = self.add_subtitle_line(lines, line_id, _("Plus Outstanding Payment"))
            for line in not_reconcile_plus:
                self.add_bank_statement_line(lines, line, line.amount)
                outstanding_plus_tot += line.amount
            line_id = self.add_total_line(lines, line_id, outstanding_plus_tot)
        # Outstanding less
        not_reconcile_less = self.env['account.bank.statement.line'].search([['statement_id.journal_id', '=', self.env.context['journal_id'].id],
                                                                             ['date', '<=', self.env.context['date_from']],
                                                                             ['journal_entry_ids', '=', False],
                                                                             ['amount', '<', 0]])
        outstanding_less_tot = 0
        if len(not_reconcile_less) > 0:
            line_id = self.add_subtitle_line(lines, line_id, _("Less outstanding receipt"))
            for line in not_reconcile_less:
                self.add_bank_statement_line(lines, line, abs(line.amount))
                outstanding_less_tot += abs(line.amount)
            line_id = self.add_total_line(lines, line_id, outstanding_less_tot)

        # Un-reconcilied bank statement lines
        move_lines = self.env['account.move.line'].search([['move_id.journal_id', '=', self.env.context['journal_id'].id],
                                                           ['move_id.statement_line_id', '=', False],
                                                           ['user_type.type', '!=', 'liquidity'],
                                                           ['date', '<=', self.env.context['date_from']]])
        unrec_tot = 0
        if len(move_lines) > 0:
            line_id = self.add_subtitle_line(lines, line_id, _("Un-Reconciled bank-statement lines"))
            for line in move_lines:
                amount = -line.debit if (line.debit > 0) else line.credit
                lines.append({
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'type': 'move_line_id',
                    'name': line.name,
                    'footnotes': self._get_footnotes('move_line_id', line.id),
                    'columns': [line.date, line.ref, amount],
                    'level': 3,
                })
                unrec_tot += amount
            line_id = self.add_total_line(lines, line_id, unrec_tot)
        
        # Final
        self.add_title_line(lines, line_id, _("Final balance"), start_amount + outstanding_plus_tot - outstanding_less_tot + unrec_tot)
        
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
        
    footnotes = fields.Many2many('account.report.footnote', 'account_context_footnote_bank_reconciliation', string=_("Footnotes"))
    journal_id = fields.Many2one('account.journal', string=_("Bank account"))
    journals = fields.One2many('account.journal', string=_("Bank Accounts"), compute=_get_bank_journals)

    @api.multi
    def add_footnote(self, type, target_id, column, number, text):
        footnote = self.env['account.report.footnote'].create(
            {'type': type, 'target_id': target_id, 'column': column, 'number': number, 'text': text}
        )
        self.write({'footnotes': [(4, footnote.id)]})

    @api.multi
    def edit_footnote(self, number, text):
        footnote = self.footnotes.filtered(lambda s: s.number == number)
        footnote.write({'text': text})

    @api.multi
    def remove_footnote(self, number):
        footnotes = self.footnotes.filtered(lambda s: s.number == number)
        self.write({'footnotes': [(3, footnotes.id)]})

    def get_report_obj(self):
        return self.env['account.bank.reconciliation']

    def get_columns_names(self):
        columns = [_("Date"), _("Reference"), _("Amount")]
        return columns
