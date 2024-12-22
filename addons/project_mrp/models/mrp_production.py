from odoo import models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _compute_analytic_distribution(self):
        project_id = self.env.context.get('project_id')
        if not project_id:
            super()._compute_analytic_distribution()
        else:
            analytic_account = self.env['project.project'].browse(project_id).analytic_account_id
            for production in self:
                production.analytic_distribution = production.analytic_distribution or {analytic_account.id: 100}
