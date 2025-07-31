# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockReplenishmentInfo(models.TransientModel):
    _inherit = 'stock.replenishment.info'
    _description = 'Stock supplier replenishment information'

    bom_id = fields.Many2one(related='orderpoint_id.bom_id')
    bom_ids = fields.Many2many('mrp.bom', compute='_compute_bom_ids', store=True)

    @api.depends('orderpoint_id')
    def _compute_bom_ids(self):
        for replenishment_info in self:
            replenishment_info.bom_ids = replenishment_info.product_id.bom_ids
