# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import format_amount

class ProjectUpdate(models.Model):
    _inherit = 'project.update'

    @api.model
    def _get_template_values(self, project):
        vals = super()._get_template_values(project)
        if project.analytic_account_id and self.user_has_groups('account.group_account_readonly'):
            vals['show_activities'] = project.budget or vals.get('show_activities')
            vals['show_profitability'] = project.budget or vals.get('show_profitability')
            budget = project.budget
            cost = -project._get_budget_items()['total']['spent']
            vals['budget'] = {
                'percentage': round((cost / budget) * 100 if budget != 0 and cost else 0, 0),
                'amount': format_amount(self.env, budget, project.currency_id),
                'spent_budget': format_amount(self.env, - cost, project.currency_id),
                'remaining_budget': format_amount(self.env, budget - cost, project.currency_id),
                'remaining_budget_percentage': round(((budget - cost) / budget) * 100 if budget != 0 else 0, 0),
            }
        return vals
