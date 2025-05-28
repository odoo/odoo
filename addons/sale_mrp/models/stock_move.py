# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models
from odoo.tools.float_utils import float_is_zero, float_round


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        res['analytic_account_id'] = self.sale_line_id.order_id.analytic_account_id
        return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _compute_sale_price(self):
        kit_lines = self.filtered(lambda move_line: move_line.move_id.bom_line_id.bom_id.type == 'phantom')
        sale_line_exploded_list_price = defaultdict(float)
        for move_line in kit_lines:
            if move_line.move_id.sale_line_id:
                unit_price = move_line.product_id.list_price
                qty = move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.move_id.sale_line_id.product_uom)
                sale_line_exploded_list_price[move_line.move_id.sale_line_id] += unit_price * qty
        sale_line_price_deviation = defaultdict(float)
        for move_line in kit_lines:
            sol = move_line.move_id.sale_line_id
            if sale_line_exploded_list_price[sol]:
                qty = move_line.product_uom_id._compute_quantity(move_line.qty_done, sol.product_uom)
                price_percentage = move_line.product_id.list_price * qty / sale_line_exploded_list_price[sol]
                exact_price = price_percentage * sol.price_total
                move_line.sale_price = float_round(exact_price, precision_rounding=sol.currency_id.rounding)
                sale_line_price_deviation[sol] += exact_price - move_line.sale_price
            else:
                unit_price = move_line.product_id.list_price
                qty = move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id)
                move_line.sale_price = unit_price * qty
        # check if the rounding error is relevant and add to the first related move_line if needed
        for sol in sale_line_price_deviation:
            if not float_is_zero(sale_line_price_deviation[sol], precision_rounding=sol.currency_id.rounding):
                move_line = (sol.move_ids.move_line_ids & kit_lines)[0]
                move_line.sale_price = float_round(move_line.sale_price + sale_line_price_deviation[sol], precision_rounding=sol.currency_id.rounding)
        super(StockMoveLine, self - kit_lines)._compute_sale_price()
