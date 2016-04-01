    # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models


class AccountBudgetAnalytic(models.TransientModel):
    _name = 'account.budget.analytic'
    _description = 'Account Budget report for analytic account'

    date_from = fields.Date(string='Start of period', required=True, default=fields.Datetime.to_string(date(date.today().year, 01, 01)))
    date_to = fields.Date(string='End of period', required=True, default=fields.Date.today())

    @api.multi
    def check_report(self):
        self.ensure_one()
        datas = {
            'ids': self.env.context.get('active_ids'),
            'model': 'account.analytic.account',
            'form': self.read()[0]
        }
        datas['form']['ids'] = datas['ids']
        analytic_accounts = self.env['account.analytic.account'].browse(self.env.context.get('active_ids'))
        return self.env['report'].get_action(analytic_accounts, 'account_budget.report_analyticaccountbudget', data=datas)
