# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _compute_website_order_line(self):
        super()._compute_website_order_line()
        for order in self:
            order.website_order_line = order.website_order_line.sorted(lambda ol: ol.gift_card_id.id)

    def _compute_cart_info(self):
        super()._compute_cart_info()
        for order in self:
            gift_card_payment_lines = order.website_order_line.filtered('gift_card_id')
            order.cart_quantity -= int(sum(gift_card_payment_lines.mapped('product_uom_qty')))

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        res = super()._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        self._recompute_gift_card_lines()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _build_gift_card(self):
        gift_card = super()._build_gift_card()
        gift_card['website_id'] = self.order_id.website_id.id
        return gift_card
