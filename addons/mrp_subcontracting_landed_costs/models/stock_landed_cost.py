# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import OrderedSet


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def _get_targeted_move_ids(self):
        res = super()._get_targeted_move_ids()
        target_moves_ids = OrderedSet()
        for move in res:
            if move.is_subcontract:
                target_moves_ids.update(move.move_orig_ids.ids)
            else:
                target_moves_ids.add(move.id)
        return self.env['stock.move'].browse(target_moves_ids)
