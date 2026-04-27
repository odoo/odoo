# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def _compute_moves_locations(self):
        super()._compute_moves_locations()
        for wizard in self:
            if wizard.product_return_moves:
                wizard.product_return_moves = wizard.product_return_moves.filtered(lambda r: not r.move_id.sale_line_id.is_rental)
