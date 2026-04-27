# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_pos_order_paid(self) -> None:
        res = super().action_pos_order_paid()
        for sale_subscription in self.lines.mapped("sale_order_origin_id").filtered("is_subscription"):
            sale_subscription._update_next_invoice_date()
        return res
