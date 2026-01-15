from odoo import api, models


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

    @api.model_create_multi
    def create(self, vals_list):
        project_id = self.env.context.get('project_id')
        if project_id:
            analytic_distribution = self.env['project.project'].browse(project_id)._get_analytic_distribution()
            if analytic_distribution:
                for vals in vals_list:
                    vals['analytic_distribution'] = vals.get('analytic_distribution', analytic_distribution)
        return super().create(vals_list)
