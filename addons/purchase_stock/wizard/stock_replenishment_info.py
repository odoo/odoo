# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import stock


class StockReplenishmentInfo(stock.StockReplenishmentInfo):
    _description = 'Stock supplier replenishment information'

    supplierinfo_id = fields.Many2one(related='orderpoint_id.supplier_id')
    supplierinfo_ids = fields.Many2many(
        'product.supplierinfo', compute='_compute_supplierinfo_ids',
        store=True)

    @api.depends('orderpoint_id')
    def _compute_supplierinfo_ids(self):
        for replenishment_info in self:
            replenishment_info.supplierinfo_ids = replenishment_info.product_id.seller_ids


class StockReplenishmentOption(stock.StockReplenishmentOption):

    def select_route(self):
        if self._context.get('replenish_id'):
            replenish = self.env['product.replenish'].browse(self._context.get('replenish_id'))
            replenish.route_id = self.route_id.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Replenish',
                'res_model': 'product.replenish',
                'res_id': replenish.id,
                'target': 'new',
                'view_mode': 'form',
            }
        return super().select_route()
