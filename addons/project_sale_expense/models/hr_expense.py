# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Expense(models.Model):
    _inherit = "hr.expense"

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        if not self.env.context.get('project_id'):
            for expense in self.filtered('sale_order_id'):
                expense.analytic_distribution = expense.sale_order_id.project_id._get_analytic_distribution()
