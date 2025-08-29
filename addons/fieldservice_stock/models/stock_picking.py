# Copyright (C) 2018 Brian McMaster
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    fsm_order_id = fields.Many2one(
        related="group_id.fsm_order_id", string="Field Service Order", store=True
    )
