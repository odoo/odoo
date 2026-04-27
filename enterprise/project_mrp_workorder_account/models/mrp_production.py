# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def write(self, vals):
        distribution_per_project = {p: p.sudo()._get_analytic_distribution() for p in self.project_id}
        res = super().write(vals)
        if 'project_id' in vals:
            for production in self:
                if production.state == 'draft':
                    continue
                for wo in production.workorder_ids:
                    wo._update_productivity_analytic(distribution_per_project.get(production.project_id, {}))
        return res
