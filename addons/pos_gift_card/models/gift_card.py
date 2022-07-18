# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class GiftCard(models.Model):
    _inherit = "gift.card"

    buy_pos_order_line_id = fields.Many2one(
        "pos.order.line",
        copy=False,
        readonly=True,
        help="Pos Order line where this gift card has been bought.",
    )
    redeem_pos_order_line_ids = fields.One2many(
        "pos.order.line", "gift_card_id", string="Pos Redeems"
    )

    @api.depends("redeem_pos_order_line_ids")
    def _compute_balance(self):
        super()._compute_balance()
        for record in self:
            confirmed_line = record.redeem_pos_order_line_ids.sudo().filtered(
                lambda l: l.order_id.state in ('paid', 'done', 'invoiced')
            )
            balance = record.balance
            if confirmed_line:
                balance -= sum(
                    confirmed_line.mapped(
                        lambda line: line.currency_id._convert(
                            line.price_unit,
                            record.currency_id,
                            record.env.company,
                            line.create_date,
                        )
                        * -1
                    )
                )
            record.balance = balance

    def can_be_used_in_pos(self):
        # expired state are computed once a day, so can be not synchro
        return self.state == 'valid' and self.balance > 0 and self.expired_date >= fields.Date.today()
