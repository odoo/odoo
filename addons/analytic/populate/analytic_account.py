from odoo import models
from odoo.tools import populate


class AnalyticAccount(models.Model):
    _inherit = "account.analytic.account"
    _populate_sizes = {
        'small': 100,
        'medium': 1_000,
        'large': 10_000,
    }

    def _populate_factories(self):
        project_plan = self._search_or_create_plan('Projects')
        department_plan = self._search_or_create_plan('Departments')
        return [
            ('company_id', populate.constant(False)),
            ('plan_id', populate.cartesian(
                [project_plan.id, department_plan.id],
                [0.99, 0.01],
            )),
            ('name', populate.constant("Account {counter}")),
        ]

    def _search_or_create_plan(self, name):
        return self.env['account.analytic.plan'].search([
            ('name', '=', name),
        ]) or self.env['account.analytic.plan'].create({
            'name': name,
        })
