# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    analytic_costs = fields.Boolean(
        compute="_compute_analytic_costs",
        store=True,
        readonly=False,
        help="Validating stock pickings will generate analytic entries for the selected project. Products set for re-invoicing will also be billed to the customer."
    )

    @api.depends('code')
    def _compute_analytic_costs(self):
        for picking_type in self:
            picking_type.analytic_costs = False
