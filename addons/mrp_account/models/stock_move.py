# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        values = super(StockMove, self)._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        if bom_line.product_id.cost_method in ('fifo', 'average'):
            values['price_unit'] = self.price_unit * bom_line.cost_repartition / 100
        return values
