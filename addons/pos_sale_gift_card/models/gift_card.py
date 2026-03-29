# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class GiftCard(models.Model):
    _inherit = "gift.card"

    def can_be_used_in_pos(self, sale_order_origin_id=False):
        can_be_used = super().can_be_used()
        return can_be_used or (sale_order_origin_id.id == self.sale_order_id.id)

    def _get_confirmed_redeem_pos_order_lines(self):
        confirmed = super()._get_confirmed_redeem_pos_order_lines()
        return confirmed.filtered(
                lambda l: not l.sale_order_line_id
            )
