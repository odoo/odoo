from odoo import models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def _compute_analytic_distribution(self):
        project_id = self.env.context.get('project_id')
        if not project_id:
            super()._compute_analytic_distribution()
        else:
            analytic_account = self.env['project.project'].browse(project_id).analytic_account_id
            for expense in self:
                expense.analytic_distribution = expense.analytic_distribution or {analytic_account.id: 100}
