# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pos_order_line_id = fields.Many2one(
        "pos.order.line",
        string="POS Order Line",
        index="btree_not_null",
        help="POS order line that generated this invoice line.",
    )

    def _get_cogs_value(self):
        self.ensure_one()
        price_unit = super()._get_cogs_value()
        sudo_order = self.move_id.sudo().pos_order_ids
        if sudo_order:
            price_unit = sudo_order._get_pos_anglo_saxon_price_unit(
                self.product_id, self.quantity,
            )
        return price_unit
