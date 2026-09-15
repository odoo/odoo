from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    wave_carrier_id = fields.Many2one(
        comodel_name="delivery.carrier",
        compute="_compute_wave_grouping",
        store=True,
        readonly=False,
    )

    @api.depends("picking_ids.carrier_id")
    def _compute_wave_grouping(self):
        super()._compute_wave_grouping()

    def _is_auto_mergeable(self, *, moves=0, pickings=0, weight=0.0):
        _debug.logic(
            "batch_auto_mergeable",
            batches=self,
            moves=moves,
            pickings=pickings,
            weight=weight,
        )
        if not super()._is_auto_mergeable(
            moves=moves, pickings=pickings, weight=weight
        ):
            return False
        max_weight = self.picking_type_id.batch_max_weight
        return not (
            weight
            and max_weight
            and sum(self.picking_ids.mapped("weight")) + weight > max_weight
        )
