# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        vals = super()._get_template_values(project)
        if project.account_id and self.env.user.has_group('account.group_account_readonly'):
            budget_items = project._get_budget_items(with_action=False)
            budgets = {
                'data': [],
                'total': {
                    'allocated': 0.0,
                    'spent': 0.0,
                },
            }
            if budget_items:
                budgets = {
                    'data': budget_items['data'],
                    'total': budget_items['total'],
                    'budget_type': budget_items['data'][0]['budget_type'] if budget_items['data'] else False,
                }
            for budget in budgets['data']:
                budget['progress'] = budget['allocated'] and (budget['spent'] - budget['allocated']) / abs(budget['allocated'])
            vals['show_activities'] = bool(project.total_budget_amount) or vals.get('show_activities', False)
            vals['show_profitability'] = bool(project.total_budget_amount) or vals.get('show_profitability', False)
            budget = project.total_budget_amount
            amount_spent = project._get_budget_items()['total']['spent']
            remaining_budget = budget - abs(amount_spent)
            vals['budget'] = {
                'percentage': abs(round((amount_spent / budget) * 100 if budget != 0 and amount_spent else 0, 0)),
                'data': budgets['data'],
                'total': budgets['total'],
                'remaining_budget_percentage': abs(round((remaining_budget / budget) * 100 if budget != 0 else 0, 0)),
                'budget_type': budgets['budget_type']
            }
        return vals
