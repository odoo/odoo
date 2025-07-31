# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockReplenishmentInfo(models.TransientModel):
    _inherit = 'stock.replenishment.info'
    _description = 'Stock supplier replenishment information'

    supplierinfo_id = fields.Many2one(related='orderpoint_id.supplier_id')
    supplierinfo_ids = fields.Many2many('product.supplierinfo', compute='_compute_supplierinfo_ids', store=True)
    show_vendor_tab = fields.Boolean(compute='_compute_show_vendor_tab')

    @api.depends('orderpoint_id')
    def _compute_supplierinfo_ids(self):
        for replenishment_info in self:
            replenishment_info.supplierinfo_ids = replenishment_info.product_id.seller_ids

    @api.depends('orderpoint_id')
    def _compute_show_vendor_tab(self):
        for replenishment_info in self:
            orderpoint = replenishment_info.orderpoint_id
            replenishment_info.show_vendor_tab = not orderpoint.route_id or (
                    orderpoint.route_id
                    and 'buy' in orderpoint.rule_ids.mapped('action')
            )


class StockReplenishmentOption(models.TransientModel):
    _inherit = 'stock.replenishment.option'

    def select_route(self):
        if self.env.context.get('replenish_id'):
            replenish = self.env['product.replenish'].browse(self.env.context.get('replenish_id'))
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
