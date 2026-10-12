# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.depends('code')
    def _compute_analytic_costs(self):
        super()._compute_analytic_costs()
        for picking_type in self:
            if picking_type.code == 'mrp_operation':
                picking_type.analytic_costs = True
