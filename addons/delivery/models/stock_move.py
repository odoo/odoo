# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons import decimal_precision as dp


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _default_uom(self):
        uom_categ_id = self.env.ref('product.product_uom_categ_kgm').id
        return self.env['product.uom'].search([('category_id', '=', uom_categ_id), ('factor', '=', 1)], limit=1)

    weight = fields.Float(compute='_cal_move_weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_uom_id = fields.Many2one('product.uom', string='Weight Unit of Measure', required=True, readonly=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for Weight", default=_default_uom)

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _cal_move_weight(self):
        for move in self.filtered(lambda moves: moves.product_id.weight > 0.00):
            move.weight = (move.product_qty * move.product_id.weight)

    def _get_new_picking_values(self):
        vals = super(StockMove, self)._get_new_picking_values()
        vals['carrier_id'] = self.sale_line_id.order_id.carrier_id.id
        return vals
