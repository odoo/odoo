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

    @api.multi
    def write(self, vals):
        if 'fiscalyear_last_day' in vals or 'fiscalyear_last_month' in vals:
            for wizard in self:
                company = wizard.company_id
                vals['fiscalyear_last_day'] = company._verify_fiscalyear_last_day(
                    company.id,
                    vals.get('fiscalyear_last_day'),
                    vals.get('fiscalyear_last_month'))
        return super(FinancialYearOpeningWizard, self).write(vals)