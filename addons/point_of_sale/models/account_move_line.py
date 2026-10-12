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
