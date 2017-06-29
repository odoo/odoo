# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons import decimal_precision as dp


class StockMove(models.Model):
    _inherit = 'stock.move'

    weight = fields.Float(compute='_cal_move_weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_uom_id = fields.Many2one('product.uom', string='Weight Unit of Measure', compute='_compute_weight_uom_id', readonly=1)

    def _compute_weight_uom_id(self):
        weight_uom_id = int(self.env['ir.config_parameter'].sudo().get_param('database_weight_uom_id'))
        for move in self:
            move.weight_uom_id = weight_uom_id

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _cal_move_weight(self):
        for move in self.filtered(lambda moves: moves.product_id.weight > 0.00):
            move.weight = (move.product_qty * move.product_id.weight)

    def _get_new_picking_values(self):
        vals = super(StockMove, self)._get_new_picking_values()
        vals['carrier_id'] = self.group_id.sale_order_id.carrier_id.id
        return vals
