# -*- coding: utf-8 -*-
# Part of Quocent. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Field to store the linked Sale Order (if any)
    sale_id = fields.Many2one('sale.order', string='Sale Order')
    # Field to store the count of linked Sale Orders
    sale_count = fields.Integer('Sale Count', compute='_compute_sale_count')

    # Compute method to set the Sale Order count
    @api.depends('sale_id')
    def _compute_sale_count(self):
        for order in self:
            order.sale_count = len(order.sale_id)

    # Action method to view the linked Sale Order
    def action_view_sale_order(self):
        if self.sale_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sale Order',
                'view_mode': 'form',
                'res_model': 'sale.order',
                'res_id': self.sale_id.id,
                'target': 'current',
            }
