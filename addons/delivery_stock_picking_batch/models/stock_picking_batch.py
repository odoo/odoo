# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    def _is_picking_auto_mergeable(self, picking):
        """ Verifies if a picking can be safely inserted into the batch without violating auto_batch_constrains.
        """
        res = super()._is_picking_auto_mergeable(picking)
        if self.picking_type_id.batch_max_weight:
            batch_weight = sum(self.picking_ids.mapped('weight'))
            res = res and (batch_weight + picking.weight <= self.picking_type_id.batch_max_weight)
        return res
