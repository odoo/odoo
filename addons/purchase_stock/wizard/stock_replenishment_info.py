# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockReplenishmentInfo(models.TransientModel):
    _inherit = 'stock.replenishment.info'
    _description = 'Stock supplier replenishment information'

    supplierinfo_id = fields.Many2one(related='orderpoint_id.supplier_id')
    supplierinfo_ids = fields.Many2many(
        'product.supplierinfo', compute='_compute_supplierinfo_ids',
        store=True)

    @api.depends('orderpoint_id')
    def _compute_supplierinfo_ids(self):
        for replenishment_info in self:
            replenishment_info.supplierinfo_ids = replenishment_info.product_id.seller_ids
