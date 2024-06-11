# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('move_ids', 'move_ids.stock_valuation_layer_ids', 'move_ids.picking_id.state')
    def _compute_purchase_price(self):
        lines_without_moves = self.browse()
        for line in self:
            product = line.product_id.with_company(line.company_id)
            if not line.has_valued_move_ids():
                lines_without_moves |= line
            elif product and product.categ_id.property_cost_method != 'standard':
                purch_price = product._compute_average_price(0, line.product_uom_qty, line.move_ids)
                if line.product_uom and line.product_uom != product.uom_id:
                    purch_price = product.uom_id._compute_price(purch_price, line.product_uom)
                to_cur = line.currency_id or line.order_id.currency_id
                line.purchase_price = line._convert_to_sol_currency(
                    purch_price,
                    product.cost_currency_id,
                )
        return super(SaleOrderLine, lines_without_moves)._compute_purchase_price()
