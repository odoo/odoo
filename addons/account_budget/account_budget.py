# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import ustr
from odoo.exceptions import UserError


# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------
class AccountBudgetPost(models.Model):
    _name = "account.budget.post"
    _description = "Budgetary Position"
    _order = "name"

    name = fields.Char(required=True)
    account_ids = fields.Many2many('account.account', 'account_budget_rel', 'budget_id', 'account_id', string='Accounts', domain=[('deprecated', '=', False)])
    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'general_budget_id', string='Budget Lines')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('account.budget.post'))


class CrossoveredBudget(models.Model):
    _name = "crossovered.budget"
    _description = "Budget"
    _inherit = ['mail.thread']

    name = fields.Char(string='Budget Name', required=True, states={'done': [('readonly', True)]})
    creating_user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    date_from = fields.Date(string='Start Date', required=True, states={'done': [('readonly', True)]})
    date_to = fields.Date(string='End Date', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'), ('cancel', 'Cancelled'), ('confirm', 'Confirmed'), ('validate', 'Validated'), ('done', 'Done')], 'Status', index=True, required=True, readonly=True, copy=False, track_visibility='always', default='draft')
    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'crossovered_budget_id', string='Budget Lines', states={'done': [('readonly', True)]}, copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('account.budget.post'))

    @api.multi
    def budget_confirm(self):
        self.write({'state': 'confirm'})

    @api.multi
    def budget_draft(self):
        self.write({'state': 'draft'})

    @api.multi
    def budget_validate(self):
        self.write({'state': 'validate'})

    @api.multi
    def budget_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def budget_done(self):
        self.write({'state': 'done'})


class CrossoveredBudgetLines(models.Model):
    _name = "crossovered.budget.lines"
    _description = "Budget Line"

    def _compute_practical_amount(self):
        for line in self:
            result = 0.0
            acc_ids = line.general_budget_id.account_ids.ids
            if line.analytic_account_id and acc_ids:
                self.env.cr.execute("SELECT SUM(amount) FROM account_analytic_line WHERE account_id=%s AND (date "
                       "between to_date(%s,'yyyy-mm-dd') AND to_date(%s,'yyyy-mm-dd')) AND "
                       "general_account_id=ANY(%s)", (line.analytic_account_id.id, line.date_from, line.date_to, acc_ids,))
                result = self.env.cr.fetchone()[0] or 0.0
            line.practical_amount = result

    def _compute_theoritical_amount(self):
        today = fields.Datetime.from_string(fields.Datetime.now())
        for line in self:
            if line.paid_date:
                if fields.Date.from_string(line.date_to) <= fields.Date.from_string(line.paid_date):
                    theo_amt = 0.00
                else:
                    theo_amt = line.planned_amount
            else:
                line_timedelta = fields.Datetime.from_string(line.date_to) - fields.Datetime.from_string(line.date_from)
                elapsed_timedelta = today - fields.Datetime.from_string(line.date_from)

                if elapsed_timedelta.days < 0:
                    # If the budget line has not started yet, theoretical amount should be zero
                    theo_amt = 0.00
                elif line_timedelta.days > 0 and today < fields.Datetime.from_string(line.date_to):
                    # If today is between the budget line date_from and date_to
                    theo_amt = (elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * line.planned_amount
                else:
                    theo_amt = line.planned_amount
            line.theoritical_amount = theo_amt

    def _compute_percentage(self):
        for line in self:
            if line.theoritical_amount != 0.00:
                line.percentage = float((line.practical_amount or 0.0) / line.theoritical_amount) * 100
            else:
                line.percentage = 0.00

    crossovered_budget_id = fields.Many2one('crossovered.budget', string='Budget', ondelete='cascade', index=True, required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    general_budget_id = fields.Many2one('account.budget.post', string='Budgetary Position', required=True)
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    paid_date = fields.Date()
    planned_amount = fields.Float(required=True, digits=0)
    practical_amount = fields.Float(compute='_compute_practical_amount', digits=0)
    theoritical_amount = fields.Float(compute='_compute_theoritical_amount', digits=0)
    percentage = fields.Float(compute='_compute_percentage', string='Achievement')
    company_id = fields.Many2one(related='crossovered_budget_id.company_id', comodel_name='res.company', string='Company', store=True, readonly=True)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'analytic_account_id', string='Budget Lines')
