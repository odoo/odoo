# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Expense(models.Model):
    _inherit = "hr.expense"

    @api.depends('sale_order_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        if not self.env.context.get('project_id'):
            for expense in self:
                if not self.sale_order_id:
                    continue
                expense.analytic_distribution = expense.sale_order_id.project_id._get_analytic_distribution()
