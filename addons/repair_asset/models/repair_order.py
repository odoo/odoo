from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class RepairOrder(models.Model):
    _inherit = "repair.order"

    # FIELDS
    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        compute="_compute_asset_id",
        store=True,
        help="The asset this repair works on, when the repaired serial is one.",
    )
    asset_kind_id = fields.Many2one(related="asset_id.kind_id")
    part_ids = fields.One2many(
        comodel_name="resource.asset.part",
        inverse_name="repair_order_id",
        string="Asset Parts",
    )

    # COMPUTE METHODS
    @api.depends("lot_id.asset_id")
    def _compute_asset_id(self):
        for repair in self:
            repair.asset_id = repair.lot_id.asset_id

    # ACTION METHODS
    def action_repair_done(self):
        res = super().action_repair_done()
        self._record_asset_parts()
        return res

    # LEDGER METHODS
    def _record_asset_parts(self):
        vals_list = []
        _debug.pipeline(
            "repair_asset_parts_recording", repairs=self.filtered("asset_id")
        )
        for repair in self.filtered("asset_id"):
            moves = repair.move_ids.filtered(
                lambda move: move.state == "done" and move.asset_position_id
            )
            removed = {
                move.asset_position_id: move
                for move in moves.filtered(
                    lambda move: move.repair_line_type in ("remove", "recycle")
                )
            }
            for move in moves.filtered(lambda move: move.repair_line_type == "add"):
                removed_move = removed.get(move.asset_position_id)
                vals_list.append(
                    {
                        "asset_id": repair.asset_id.id,
                        "position_id": move.asset_position_id.id,
                        "product_id": move.product_id.id,
                        "serial": move.move_line_ids.lot_id[:1].name,
                        "user_id": repair.user_id.id,
                        "repair_order_id": repair.id,
                        "source": "repair",
                        "removed_serial": removed_move
                        and removed_move.move_line_ids.lot_id[:1].name,
                        "removed_returned": bool(removed_move),
                        "state": "installed",
                    }
                )
        _debug.logic("repair_asset_parts_recorded", repairs=self, parts=len(vals_list))
        if vals_list:
            self.env["resource.asset.part"].create(vals_list)
