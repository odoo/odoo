# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _cal_price(self, consumed_moves):
        finished_move = self.move_finished_ids.filtered(lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity_done > 0)
        # Take the price unit of the reception move
        if finished_move.move_dest_ids.is_subcontract:
            self.extra_cost = finished_move.move_dest_ids._get_price_unit()
        return super()._cal_price(consumed_moves=consumed_moves)
