# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def _get_targeted_move_ids(self):
        res = super()._get_targeted_move_ids()
        target_moves = self.env['stock.move']
        for move in res:
            if move.is_subcontract:
                target_moves |= move.move_orig_ids
            else:
                target_moves |= move
        return target_moves
