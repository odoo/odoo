# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'analytic_account_id', 'Budget Lines')
    total_planned_amount = fields.Monetary(compute="_compute_total_planned_amount")
    total_practical_amount = fields.Monetary(compute="_compute_total_practical_amount")

    @api.depends('crossovered_budget_line.planned_amount')
    def _compute_total_planned_amount(self):
        rates = {}
        for account in self:
            currency = account.currency_id or self.env.company.currency_id
            company = account.company_id or self.env.company
            total_planned_amount = 0
            for line in account.crossovered_budget_line:
                if line.currency_id == currency:
                    total_planned_amount += line.planned_amount
                    continue
                rate_key = (line.currency_id, currency, company, line.date_from)
                if rates.get(rate_key):
                    rate = rates[rate_key]
                else:
                    rate = rates[rate_key] = currency._get_conversion_rate(*rate_key)
                    rates[rate_key] = rate
                total_planned_amount += line.planned_amount * rate
            account.total_planned_amount = currency.round(total_planned_amount)

    @api.depends('crossovered_budget_line.practical_amount')
    def _compute_total_practical_amount(self):
        rates = {}
        for account in self:
            company = account.company_id or self.env.company
            currency = account.currency_id or company.currency_id
            total_practical_amount = 0
            for line in account.crossovered_budget_line:
                if line.currency_id == currency:
                    total_practical_amount += line.practical_amount
                    continue
                rate_key = (line.currency_id, currency, company, line.date_from)
                if rate_key in rates:
                    rate = rates[rate_key]
                else:
                    rate = rates[rate_key] = currency._get_conversion_rate(*rate_key)
                total_practical_amount += line.practical_amount * rate
            account.total_practical_amount = currency.round(total_practical_amount)
