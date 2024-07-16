# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Expense(models.Model):
    _inherit = "hr.expense"

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for expense in self:
            if not expense.sale_order_id:
                continue
            analytic_distribution = expense.sale_order_id.project_id._get_analytic_distribution()
            if analytic_distribution:
                expense.analytic_distribution = analytic_distribution
