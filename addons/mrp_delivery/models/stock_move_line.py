# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _compute_sale_price(self):
        kit_lines = self.filtered(lambda move_line: move_line.move_id.bom_line_id.bom_id.type == 'phantom')
        sale_line_exploded_list_price = defaultdict(float)
        for sol in kit_lines.move_id.sale_line_id:
            bom = self.env['mrp.bom'].sudo()._bom_find(sol.product_id, company_id=sol.company_id.id, bom_type='phantom')[sol.product_id]
            _, bom_lines = bom.explode(sol.product_id, sol.product_uom_id._compute_quantity(sol.product_uom_qty, sol.product_id.uom_id))
            sale_line_exploded_list_price[sol] = sum(bom_line.product_uom_id._compute_quantity(data['qty'], bom_line.product_id.uom_id) * bom_line.product_id.list_price for bom_line, data in bom_lines)
        sale_line_price_deviation = defaultdict(float)
        for move_line in kit_lines:
            sol = move_line.move_id.sale_line_id
            if sale_line_exploded_list_price[sol]:
                price_percentage = move_line.product_id.list_price * move_line.quantity / sale_line_exploded_list_price[sol]
                exact_price = price_percentage * sol.price_total
                move_line.sale_price = sol.currency_id.round(exact_price)
                sale_line_price_deviation[sol] += exact_price - move_line.sale_price
            else:
                unit_price = move_line.product_id.list_price
                move_line.sale_price = unit_price * move_line.quantity
        # check if the rounding error is relevant and add to the first related move_line if needed
        for sol in sale_line_price_deviation:
            if not sol.currency_id.is_zero(sale_line_price_deviation[sol]):
                move_line = (sol.move_ids.move_line_ids & kit_lines)[0]
                move_line.sale_price = sol.currency_id.round(move_line.sale_price + sale_line_price_deviation[sol])
        super(StockMoveLine, self - kit_lines)._compute_sale_price()
