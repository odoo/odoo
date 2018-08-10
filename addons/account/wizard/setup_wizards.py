# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class FinancialYearOpeningWizard(models.TransientModel):
    _name = 'account.financial.year.op'

    company_id = fields.Many2one(comodel_name='res.company', required=True)
    opening_move_posted = fields.Boolean(string='Opening Move Posted', compute='_compute_opening_move_posted')
    opening_date = fields.Date(string='Opening Date', required=True, related='company_id.account_opening_date', help="Date from which the accounting is managed in Odoo. It is the date of the opening entry.")
    fiscalyear_last_day = fields.Integer(related="company_id.fiscalyear_last_day", required=True,
                                         help="The last day of the month will be taken if the chosen day doesn't exist.")
    fiscalyear_last_month = fields.Selection(selection=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')],
                                             related="company_id.fiscalyear_last_month",
                                             required=True,
                                             help="The last day of the month will be taken if the chosen day doesn't exist.")
    account_setup_fy_data_done = fields.Boolean(string='Financial year setup marked as done', compute="_compute_setup_marked_done")

    @api.depends('company_id.account_setup_fy_data_done')
    def _compute_setup_marked_done(self):
        for record in self:
            record.account_setup_fy_data_done = record.company_id.account_setup_fy_data_done

    @api.depends('company_id.account_opening_move_id')
    def _compute_opening_move_posted(self):
        for record in self:
            record.opening_move_posted = record.company_id.opening_move_posted()

    def mark_as_done(self):
        """ Forces fiscal year setup state to 'done'."""
        self.company_id.account_setup_fy_data_done = True

    def unmark_as_done(self):
        """ Forces fiscal year setup state to 'undone'."""
        self.company_id.account_setup_fy_data_done = False


class OpeningAccountMoveWizard(models.TransientModel):
    _name = 'account.opening'

    company_id = fields.Many2one(comodel_name='res.company', required=True)
    opening_move_id = fields.Many2one(string='Opening Journal Entry', comodel_name='account.move', related='company_id.account_opening_move_id')
    currency_id = fields.Many2one(comodel_name='res.currency', related='opening_move_id.currency_id')
    opening_move_line_ids = fields.One2many(string='Opening Journal Items', related="opening_move_id.line_ids")
    journal_id = fields.Many2one(string='Journal', comodel_name='account.journal', required=True, related='opening_move_id.journal_id')
    date = fields.Date(string='Opening Date', required=True, related='opening_move_id.date')

    def validate(self):
        self.opening_move_id.post()

    @api.onchange('opening_move_line_ids')
    def opening_move_line_ids_changed(self):
        debit_diff, credit_diff = self.company_id.get_opening_move_differences(self.opening_move_line_ids)

        unaffected_earnings_account = self.company_id.get_unaffected_earnings_account()
        balancing_line = self.opening_move_line_ids.filtered(lambda x: x.account_id == unaffected_earnings_account)

        if balancing_line:
            if not self.opening_move_line_ids == balancing_line and (debit_diff or credit_diff):
                balancing_line.debit = credit_diff
                balancing_line.credit = debit_diff
            else:
                self.opening_move_line_ids -= balancing_line
        elif debit_diff or credit_diff:
            balancing_line = self.env['account.move.line'].new({
                        'name': _('Automatic Balancing Line'),
                        'move_id': self.company_id.account_opening_move_id.id,
                        'account_id': unaffected_earnings_account.id,
                        'debit': credit_diff,
                        'credit': debit_diff,
                        'company_id': self.company_id,
                    })
            self.opening_move_line_ids += balancing_line
