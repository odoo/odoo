# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_discount_lines(self):
        lines = super()._get_discount_lines()
        discount_line_ids = []
        for line in self - lines:
            pos_orders = line.move_id.sudo().pos_order_ids
            if not pos_orders:
                continue
            reward_discount_products = pos_orders.lines.filtered(
                lambda pol: pol.is_reward_line and pol.reward_id.reward_type == 'discount'
            ).product_id
            if line.product_id in reward_discount_products:
                discount_line_ids.append(line.id)
        if discount_line_ids:
            lines |= self.browse(discount_line_ids)
        return lines
