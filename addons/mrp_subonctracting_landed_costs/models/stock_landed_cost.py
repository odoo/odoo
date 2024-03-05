# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def _get_targeted_move_ids(self):
        moves = super()._get_targeted_move_ids()
        return moves.filtered(lambda m: not m.is_subcontract) | moves.filtered('is_subcontract').move_orig_ids
