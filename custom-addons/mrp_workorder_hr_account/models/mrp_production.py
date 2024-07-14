# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def write(self, vals):
        old_dists = {production: production.analytic_distribution for production in self}
        res = super().write(vals)
        for production in self:
            if 'analytic_distribution' in vals and production.state != 'draft':
                for wo in production.workorder_ids:
                    wo._update_productivity_analytic(old_dists[production])
        return res
