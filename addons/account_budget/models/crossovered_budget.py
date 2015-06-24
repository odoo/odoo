# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from openerp.tools import ustr
from openerp.exceptions import UserError

# ---------------------------------------------------------
# Utils
# ---------------------------------------------------------


def strToDate(dt):
    return fields.Date.from_string(dt)


def strToDatetime(strdate):
    return fields.Datetime.from_string(strdate)


class CrossoveredBudget(models.Model):
    _name = "crossovered.budget"
    _description = "Budget"

    name = fields.Char(string='Name', required=True, states={'done': [('readonly', True)]})
    code = fields.Char(string='Code', size=16, required=True, states={'done': [('readonly', True)]})
    creating_user_id = fields.Many2one('res.users', string='Responsible User', default=lambda self: self.env.uid,)
    validating_user_id = fields.Many2one('res.users', string='Validate User', readonly=True)
    date_from = fields.Date(string='Start Date', required=True, states={'done': [('readonly', True)]})
    date_to = fields.Date(string='End Date', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'), ('cancel', 'Cancelled'), ('confirm', 'Confirmed'), ('validate', 'Validated'), ('done', 'Done')], string='Status', index=True, required=True, readonly=True, default='draft')
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
        return self.write({
            'state': 'validate',
            'validating_user_id': self.env.uid,
        })

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
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    general_budget_id = fields.Many2one('account.budget.post', string='Budgetary Position', required=True)
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    paid_date = fields.Date(string='Paid Date')
    planned_amount = fields.Float(string='Planned Amount', required=True, digits=0)
    practical_amount = fields.Float(compute='_compute_practical_amount', string='Practical Amount', digits=0)
    theoritical_amount = fields.Float(compute='_compute_theoretical_amount', string='Theoretical Amount', digits=0)
    percentage = fields.Float(compute='_compute_percentage', string='Percentage')
    company_id = fields.Many2one(related='crossovered_budget_id.company_id', comodel_name='res.company', string='Company', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', help='Utility field to express amount currency')

    @api.multi
    def _prac_amt(self):
        result = {}
        amount = 0.0
        AccountAnalyticLine = self.env['account.analytic.line']
        for line in self:
            acc_ids = self.general_budget_id.account_ids.ids
            if not acc_ids:
                raise UserError(_("The Budget '%s' has no accounts!") % ustr(self.general_budget_id.name))
            if self.analytic_account_id.id:
                analytic_lines = AccountAnalyticLine.search([('account_id', '=', self.analytic_account_id.id), ('date', '>=', self.date_from), ('date', '<=', self.date_to), ('general_account_id', 'in', acc_ids)])
                for analytic_line in analytic_lines:
                    amount += analytic_line.amount
            result[line.id] = amount
        return result

    @api.multi
    def _compute_practical_amount(self):
        for line in self:
            line.practical_amount = line._prac_amt()[line.id]

    @api.multi
    def _theo_amt(self):
        res = {}
        for line in self:
            today = strToDatetime(fields.Datetime.now())

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

            res[line.id] = theo_amt
        return res

    @api.multi
    def _compute_theoretical_amount(self):
        for line in self:
            line.theoritical_amount = line._theo_amt()[line.id]

    @api.multi
    def _compute_percentage(self):
        for line in self:
            if line.theoritical_amount != 0.00:
                line.percentage = float((line.practical_amount or 0.0) / line.theoritical_amount) * 100
            else:
                line.percentage = 0.00

    @api.one
    def _get_company_currency(self):
        self.currency_id = self.company_id.currency_id if self.company_id else self.env.user.company_id.currency_id
