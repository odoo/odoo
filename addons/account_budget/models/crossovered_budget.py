# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import ustr


def strToDate(dt):
    return fields.Date.from_string(dt)


def strToDatetime(strdate):
    return fields.Datetime.from_string(strdate)


class CrossoveredBudget(models.Model):
    _name = "crossovered.budget"
    _description = "Budget"
    _inherit = ['mail.thread']

    name = fields.Char(string='Budget Name', required=True, states={'done': [('readonly', True)]})
    creating_user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.uid,)
    date_from = fields.Date(string='Start Date', required=True, states={'done': [('readonly', True)]})
    date_to = fields.Date(string='End Date', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'), ('cancel', 'Cancelled'), ('confirm', 'Confirmed'), ('validate', 'Validated'), ('done', 'Done')], 'Status', index=True, required=True, readonly=True, copy=False, track_visibility='always', default='draft')
    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'crossovered_budget_id', string='Budget Lines', states={'done': [('readonly', True)]}, copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('account.budget.post'))

    @api.multi
    def budget_confirm(self):
        return self.write({'state': 'confirm'})

    @api.multi
    def budget_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def budget_validate(self):
        return self.write({'state': 'validate'})

    @api.multi
    def budget_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def budget_done(self):
        return self.write({'state': 'done'})


class CrossoveredBudgetLines(models.Model):
    _name = "crossovered.budget.lines"
    _description = "Budget Line"

    crossovered_budget_id = fields.Many2one('crossovered.budget', string='Budget', ondelete='cascade', index=True, required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', domain=[('account_type', '=', 'normal')])
    general_budget_id = fields.Many2one('account.budget.post', string='Budgetary Position', required=True)
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    paid_date = fields.Date('Paid Date')
    planned_amount = fields.Float(string='Planned Amount', required=True, digits=0)
    practical_amount = fields.Float(compute='_prac', string='Practical Amount', digits=0)
    theoritical_amount = fields.Float(compute='_theo', string='Theoretical Amount', digits=0)
    percentage = fields.Float(compute='_perc', string='Achievement')
    company_id = fields.Many2one(related='crossovered_budget_id.company_id', comodel_name='res.company', string='Company', store=True, readonly=True)

    def _prac(self):
        AccountAnalyticLine = self.env['account.analytic.line']
        for line in self:
            amount = 0.0
            acc_ids = line.general_budget_id.account_ids.ids
            if not acc_ids:
                raise UserError(_("The Budget '%s' has no accounts!") % ustr(line.general_budget_id.name))
            if line.analytic_account_id:
                analytic_lines = AccountAnalyticLine.search([('account_id', '=', line.analytic_account_id.id), ('date', '>=', line.date_from), ('date', '<=', line.date_to), ('general_account_id', 'in', acc_ids)])
                for analytic_line in analytic_lines:
                    amount += analytic_line.amount
            line.practical_amount = amount

    def _theo(self):
        today = strToDatetime(fields.Datetime.now())
        for line in self:
            if line.paid_date:
                if strToDate(line.date_to) <= strToDate(line.paid_date):
                    theo_amt = 0.00
                else:
                    theo_amt = line.planned_amount
            else:
                line_timedelta = strToDatetime(line.date_to) - strToDatetime(line.date_from)
                elapsed_timedelta = today - (strToDatetime(line.date_from))

                if elapsed_timedelta.days < 0:
                    # If the budget line has not started yet, theoretical amount should be zero
                    theo_amt = 0.00
                elif line_timedelta.days > 0 and today < strToDatetime(line.date_to):
                    # If today is between the budget line date_from and date_to
                    theo_amt = (elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * line.planned_amount
                else:
                    theo_amt = line.planned_amount
            line.theoritical_amount = theo_amt

    def _perc(self):
        for line in self:
            if line.theoritical_amount != 0.00:
                line.percentage = float((line.practical_amount or 0.0) / line.theoritical_amount) * 100
            else:
                line.percentage = 0.00
