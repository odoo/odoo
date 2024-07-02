# Part of Odoo. See LICENSE file for full copyright and licensing details.
from functools import reduce

from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        ProjectProject = self.env['project.project']
        for line in self:
            project_id = line._context.get('project_id')
            project = ProjectProject.browse(project_id) if project_id else line.order_id.project_id
            if project:
                line.analytic_distribution = {reduce(lambda acc, el: f"{acc},{el}", project._get_analytic_account_ids().ids): 100}

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._recompute_recordset(fnames=['analytic_distribution'])
        return lines
