# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class BudgetAnalytic(models.Model):
    _inherit = 'budget.analytic'

    @api.model_create_multi
    def create(self, vals_list):
        budgets = super().create(vals_list)
        if len(budgets) == 1 and self.env.context.get('project_update'):  # Creation with Add Budget button in project update
            budgets.action_budget_confirm()
        return budgets
