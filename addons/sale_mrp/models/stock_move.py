# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models



class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _compute_sale_price(self):
        def get_bom_component_price_ratio(bom_id):
            price_ratio_vals = dict()
            product_id = bom_id.product_id or bom_id.product_tmpl_id.product_variant_id
            total_bom_price = product_id._compute_bom_price(bom_id)
            for bom_line in bom_id.bom_line_ids:
                price_ratio_vals.update({
                    bom_line.product_id.id: bom_line.product_id.standard_price / total_bom_price
                })
            return price_ratio_vals

        kit_lines = self.filtered(lambda move_line: move_line.move_id.sale_line_id and move_line.move_id.bom_line_id.bom_id.type == 'phantom')
        price_ratio_vals = get_bom_component_price_ratio(kit_lines.move_id.bom_line_id.bom_id) if kit_lines else {}
        for move_line in kit_lines:
            discount = move_line.move_id.sale_line_id.get_discount_amount()
            sale_unit_price = (move_line.move_id.sale_line_id.price_total - discount) / move_line.move_id.sale_line_id.product_uom_qty
            unit_price = sale_unit_price * price_ratio_vals.get(move_line.product_id.id, 0)
            qty = move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id)
            move_line.sale_price = unit_price * qty
        super(StockMoveLine, self - kit_lines)._compute_sale_price()
