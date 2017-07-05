# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from odoo.tools.float_utils import float_round, float_compare, float_is_zero


class FinancialYearOpeningWizard(models.TransientModel):
    _name = 'account.financial.year.op'

    company_id = fields.Many2one(comodel_name='res.company')
    opening_move_posted = fields.Boolean(string='Opening move posted', compute='_compute_opening_move_posted')
    opening_date = fields.Date(string='Opening Date', required=True, related='company_id.account_opening_date', help="Date from which the accounting is managed in Odoo. It is the date of the opening entry.")
    fiscalyear_last_day = fields.Integer(related="company_id.fiscalyear_last_day", required=True)
    fiscalyear_last_month = fields.Selection(selection=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')],
                                             related="company_id.fiscalyear_last_month",
                                             required=True)
    account_setup_financial_year_data_marked_done = fields.Boolean(string='Financial year setup marked as done', compute="_compute_setup_marked_done")

    @api.depends('company_id.account_setup_financial_year_data_marked_done')
    def _compute_setup_marked_done(self):
        for record in self:
            record.account_setup_financial_year_data_marked_done = record.company_id.account_setup_financial_year_data_marked_done

    @api.depends('company_id.account_opening_move_id')
    def _compute_opening_move_posted(self):
        for record in self:
            record.opening_move_posted = record.company_id.opening_move_posted()

    def mark_as_done(self):
        """ Forces fiscal year setup state to 'done'.
        """
        self.company_id.account_setup_financial_year_data_marked_done = True

    def unmark_as_done(self):
        """ Forces fiscal year setup state to 'undone'.
        """
        self.company_id.account_setup_financial_year_data_marked_done = False

class OpeningAccountMoveWizard(models.TransientModel):
    _name = 'account.opening'

    company_id = fields.Many2one(comodel_name='res.company')
    opening_move_id = fields.Many2one(string='Opening move', comodel_name='account.move', related='company_id.account_opening_move_id')
    currency_id = fields.Many2one(comodel_name='res.currency', related='opening_move_id.currency_id')
    opening_move_line_ids = fields.One2many(string='Opening move lines', related="opening_move_id.line_ids")
    journal_id = fields.Many2one(string='Journal', comodel_name='account.journal', required=True, related='opening_move_id.journal_id')
    date = fields.Date(string='Opening Date', required=True, related='opening_move_id.date')

    def validate(self):
        """ Called by this wizard's 'post' button.
        """
        self.opening_move_id.post() # This will raise an error if we don't have debit = credit
