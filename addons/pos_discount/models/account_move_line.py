# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_discount_lines(self):
        lines = super()._get_discount_lines()
        discount_line_ids = []
        for line in self - lines:
            pos_orders = line.move_id.sudo().pos_order_ids
            if pos_orders and line.product_id in pos_orders.config_id.discount_product_id:
                discount_line_ids.append(line.id)
        if discount_line_ids:
            lines |= self.browse(discount_line_ids)
        return lines
