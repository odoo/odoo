# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _create_in_svl(self, forced_quantity=None):
        res = super()._create_in_svl(forced_quantity=forced_quantity)
        for move in self:
            if not move.production_id or not move.note:
                continue
            if move.stock_valuation_layer_ids:
                move.stock_valuation_layer_ids[0].description += '\n' + move.note
        return res
