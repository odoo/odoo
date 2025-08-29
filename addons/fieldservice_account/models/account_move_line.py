# Copyright 2019 Akretion <raphael.reverdy@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    fsm_order_ids = fields.Many2many(
        "fsm.order",
        "fsm_order_account_move_line_rel",
        "account_move_line_id",
        "fsm_order_id",
        string="FSM Orders",
        readonly=True,
        copy=False,
    )
