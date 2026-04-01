# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockReplenishmentInfo(models.TransientModel):
    _inherit = 'stock.replenishment.info'
    _description = 'Stock supplier replenishment information'

    bom_id = fields.Many2one(related='orderpoint_id.bom_id')
    bom_ids = fields.Many2many('mrp.bom', compute='_compute_bom_ids', store=True)
    show_bom_tab = fields.Boolean(compute='_compute_show_bom_tab')

    @api.depends('orderpoint_id')
    def _compute_bom_ids(self):
        for replenishment_info in self:
            replenishment_info.bom_ids = replenishment_info.product_id.bom_ids

    @api.depends('orderpoint_id')
    def _compute_show_bom_tab(self):
        for replenishment_info in self:
            orderpoint = replenishment_info.orderpoint_id
            replenishment_info.show_bom_tab = not orderpoint.route_id or (
                    orderpoint.route_id
                    and 'manufacture' in orderpoint.rule_ids.mapped('action')
            )
