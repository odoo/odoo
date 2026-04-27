# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _
from odoo.tools import date_utils, format_date
from itertools import product
from functools import partial


class BudgetSplitWizard(models.TransientModel):
    _name = 'budget.split.wizard'
    _description = 'Budget Split Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    period = fields.Selection([
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year')
    ], string='Period', required=True, default='year')
    analytical_plan_ids = fields.Many2many('account.analytic.plan', string='Analytic Plans', required=True)

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'date_from' in fields_list and not defaults.get('date_from'):
            defaults['date_from'] = date_utils.start_of(fields.Date.context_today(self), 'year')
        if 'date_to' in fields_list and not defaults.get('date_to'):
            defaults['date_to'] = date_utils.end_of(fields.Date.context_today(self), 'year')
        return defaults

    def action_budget_split(self):
        self.ensure_one()
        account_dict = {rec._column_name(): rec.account_ids.ids for rec in self.analytical_plan_ids}
        budget_lines = [(0, 0, line) for line in [dict(zip(account_dict.keys(), combination)) for combination in product(*account_dict.values())]]
        if self.period == 'year':
            name = partial(format_date, self.env, date_format='yyyy')
            step = relativedelta(years=1)
        elif self.period == 'month':
            name = partial(format_date, self.env, date_format='MMMM yyyy')
            step = relativedelta(months=1)
        elif self.period == 'quarter':
            name = partial(format_date, self.env, date_format='QQQ yyyy')
            step = relativedelta(months=3)

        budget_vals = []
        for date_from in date_utils.date_range(self.date_from, self.date_to, step):
            date_to = date_from + step - relativedelta(days=1)
            if date_to > self.date_to:
                break
            budget_vals.append({
                'name': _('Budget %s', name(date_from)),
                'date_from': date_from,
                'date_to': date_to,
                'budget_type': 'expense',
                'budget_line_ids': budget_lines,
            })
        budgets = self.env['budget.analytic'].create(budget_vals)
        return {
            'name': _('Budgets'),
            'view_mode': 'list',
            'res_model': 'budget.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', budgets.budget_line_ids.ids)],
            'context': {'group_by': 'budget_analytic_id'},
        }
