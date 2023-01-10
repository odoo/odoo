# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class GiftCard(models.Model):
    _inherit = "gift.card"

    buy_line_id = fields.Many2one("sale.order.line", copy=False, readonly=True,
                                  help="Sale Order line where this gift card has been bought.")
    redeem_line_ids = fields.One2many('sale.order.line', 'gift_card_id', string="Redeems")

    @api.depends("redeem_line_ids")
    def _compute_balance(self):
        super()._compute_balance()
        for record in self:
            confirmed_line = record.redeem_line_ids.filtered(lambda l: l.state in ('sale', 'done'))
            balance = record.balance
            if confirmed_line:
                balance -= sum(confirmed_line.mapped(
                    lambda line: line.currency_id._convert(line.price_unit, record.currency_id, record.env.company, line.create_date) * -1
                ))
            record.balance = balance
