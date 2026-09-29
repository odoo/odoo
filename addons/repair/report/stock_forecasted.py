# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockForecasted_Product_Product(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _get_reservation_data(self, move):
        if move.repair_id and move.repair_line_type:
            return False
        return super()._get_reservation_data(move)
