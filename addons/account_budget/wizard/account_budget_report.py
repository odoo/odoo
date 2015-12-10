# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models


class AccountBudgetReport(models.TransientModel):

    _name = "account.budget.report"
    _description = "Account Budget report for analytic account"

    date_from = fields.Date(string='Start of period', required=True, default=fields.Datetime.to_string(date(date.today().year, 01, 01)))
    date_to = fields.Date(string='End of period', required=True, default=fields.Date.today())

    @api.multi
    def check_report(self):
        self.ensure_one()
        datas = {
            'ids': self.env.context.get('active_ids'),
            'model': 'account.budget.post',
            'form': self.read()[0]
        }
        datas['form']['ids'] = datas['ids']
        datas['form']['report'] = 'analytic-full'
        analytic_account = self.env['account.budget.post'].browse(self.env.context.get('active_ids'))
        return self.env['report'].get_action(analytic_account, 'account_budget.report_budget', data=datas)
