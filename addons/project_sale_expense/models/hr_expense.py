# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        if not self.env.context.get('project_id'):
            for expense in self.filtered('sale_order_id'):
                expense.analytic_distribution = expense.sale_order_id.project_id._get_analytic_distribution()

    def action_post(self):
        """ When creating the move of the expense, if the AA is given in the project of the SO, we take it as reference in the distribution.
            Otherwise, we create a AA for the project of the SO and set the distribution to it.
        """
        for expense in self:
            project = expense.sale_order_id.project_id
            if not project or expense.analytic_distribution:
                continue
            if not project.account_id:
                project._create_analytic_account()
            expense.analytic_distribution = project._get_analytic_distribution()
        return super().action_post()
