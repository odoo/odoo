# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_sale_stock_move(self):
        # MO finished goods moves are linked to the sale line for traceability, but should not be
        # considered as incoming moves counterbalancing the delivery moves in cogs price unit
        moves = super()._get_sale_stock_move()
        return moves.filtered(lambda m: not m.production_id)
