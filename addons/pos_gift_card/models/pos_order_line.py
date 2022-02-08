# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    generated_gift_card_ids = fields.One2many(
        "gift.card", "buy_pos_order_line_id", string="Bought Gift Card"
    )
    gift_card_id = fields.Many2one(
        "gift.card", help="Deducted from this Gift Card", copy=False
    )

    def _is_not_sellable_line(self):
        return self.gift_card_id or super()._is_not_sellable_line()

    def _create_gift_cards(self):
        return self.env["gift.card"].create(
            [self._build_gift_card() for _ in range(int(self.qty))]
        )

    def _build_gift_card(self):
        return {
            "initial_amount": self.order_id.currency_id._convert(
                self.price_unit,
                self.company_id.currency_id,
                self.company_id,
                fields.Date.today(),
            ),
            "buy_pos_order_line_id": self.id,
        }
