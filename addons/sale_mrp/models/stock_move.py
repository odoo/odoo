# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        res['analytic_account_id'] = self.sale_line_id.order_id.analytic_account_id
        if self.sale_line_id.order_id.analytic_account_id:
            res['analytic_distribution'] = {self.sale_line_id.order_id.analytic_account_id.id: 100}
        return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _compute_sale_price(self):
        kit_lines = self.filtered(lambda move_line: move_line.move_id.bom_line_id.bom_id.type == 'phantom')
        for move_line in kit_lines:
            bom_id = move_line.move_id.bom_line_id.bom_id
            global_discount = move_line.move_id.sale_line_id.get_global_discount()
            sale_unit_price = move_line.move_id.sale_line_id.price_reduce_taxinc - global_discount
            move_line_qty = move_line.quantity
            total_list_price = sum(bom_id.bom_line_ids.mapped("product_id.list_price"))
            bom_components_total_qty = sum(bom_id.bom_line_ids.mapped("product_qty"))
            bom_line_product_qty = sum(bom_id.bom_line_ids.filtered(lambda line: line.product_id == move_line.product_id).mapped('product_qty'))
            if total_list_price:
                list_price_ratio = move_line.product_id.list_price / total_list_price
                unit_price = ((sale_unit_price * list_price_ratio) / move_line_qty) * ((1 / bom_line_product_qty) * move_line_qty)
            else:
                unit_price = (sale_unit_price * (bom_line_product_qty / bom_components_total_qty)) / bom_line_product_qty
            qty = move_line.product_uom_id._compute_quantity(move_line_qty, move_line.product_id.uom_id)
            move_line.sale_price = unit_price * qty
        super(StockMoveLine, self - kit_lines)._compute_sale_price()
