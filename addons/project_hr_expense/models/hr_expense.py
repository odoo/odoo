from odoo import models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def _compute_analytic_distribution(self):
        project_id = self.env.context.get('project_id')
        if not project_id:
            super()._compute_analytic_distribution()
        else:
            analytic_distribution = self.env['project.project'].browse(project_id)._get_analytic_distribution()
            for expense in self:
                expense.analytic_distribution = expense.analytic_distribution or analytic_distribution
