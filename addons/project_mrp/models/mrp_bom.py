from odoo import models, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.onchange('product_id')
    def _onchange_analytic_distribution(self):
        project_id = self._context.get('project_id', False)
        if not project_id:
            super()._onchange_analytic_distribution()
        else:
            analytic_account = self.env['project.project'].browse(project_id).analytic_account_id
            for bom in self:
                bom.analytic_distribution = bom.analytic_distribution or {analytic_account.id: 100}
