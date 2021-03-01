# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('move_ids', 'move_ids.stock_valuation_layer_ids', 'order_id.picking_ids.state')
    def _compute_purchase_price(self):
        lines_without_moves = self.browse()
        for line in self:
            if not line.move_ids:
                lines_without_moves |= line
            else:
                product_currency_purchase_price = line.product_id.with_company(line.company_id)._compute_average_price(0, line.product_uom_qty, line.move_ids)

                # put by me because at a sale in another currency we are going to subtract 2 different currencies
                # code for from and to currency from sale_margin
                product = line.product_id
                fro_cur = product.cost_currency_id
                to_cur = line.currency_id or line.order_id.currency_id
                line.purchase_price = fro_cur._convert(
                    from_amount=product_currency_purchase_price,
                    to_currency=to_cur,
                    company=line.company_id or self.env.company,
                    date=line.order_id.date_order or fields.Date.today(),
                    round=False,
                ) if to_cur and product_currency_purchase_price else product_currency_purchase_price


        return super(SaleOrderLine, lines_without_moves)._compute_purchase_price()
