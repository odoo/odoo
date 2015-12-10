# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models


class AccountBudgetCrossveredReport(models.TransientModel):
    _name = "account.budget.crossvered.report"
    _description = "Account Budget crossovered report"

    date_from = fields.Date(string='Start of period', required=True, default=fields.Datetime.to_string(date(date.today().year, 01, 01)))
    date_to = fields.Date(string='End of period', required=True, default=fields.Date.today())

    @api.multi
    def check_report(self):
        self.ensure_one()
        datas = {
            'ids': self.env.context.get('active_ids'),
            'model': 'crossovered.budget',
            'form': self.read()[0]
        }
        datas['form']['report'] = 'analytic-full'
        analytic_accounts = self.env['crossovered.budget'].browse(self.env.context.get('active_ids'))
        return self.env['report'].get_action(analytic_accounts, 'account_budget.report_crossoveredbudget', data=datas)
