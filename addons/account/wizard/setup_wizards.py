# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from odoo.tools.float_utils import float_round, float_compare, float_is_zero

import logging
_logger=logging.getLogger(__name__)

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
        self.opening_move_id.post()

    @api.onchange('opening_move_line_ids','opening_move_line_ids')
    def opening_move_line_ids_changed(self):
        opening_differences = self.company_id.get_opening_move_differences(self.opening_move_line_ids)
        credit_difference = opening_differences['credit']
        debit_difference = opening_differences['debit']

        unaffected_earnings_account = self.company_id.get_unaffected_earnings_account()
        balancing_line = self.opening_move_line_ids.filtered(lambda x: x.account_id == unaffected_earnings_account)

        _logger.warn("--------ON CHANGE CALLED"+str(debit_difference)+str(credit_difference))
        if balancing_line:
            if not self.opening_move_line_ids == balancing_line and (debit_difference or credit_difference):
                _logger.warn("MODIFY "+str(self.opening_move_line_ids.ids))
                balancing_line.debit = credit_difference
                balancing_line.credit = debit_difference
            else:
                _logger.warn("DELETE "+str(self.opening_move_line_ids.ids))
                self.opening_move_line_ids -= balancing_line
        elif debit_difference or credit_difference:
            _logger.warn("ADD  "+str(self.opening_move_line_ids.ids))
            balancing_line = self.env['account.move.line'].new({
                        'name': 'Opening Move Automatic Balancing Line',
                        'move_id': self.company_id.account_opening_move_id.id,
                        'account_id': unaffected_earnings_account.id,
                        'debit': credit_difference,
                        'credit': debit_difference,
                        'company_id': self.company_id,
                    })
            self.opening_move_line_ids += balancing_line
