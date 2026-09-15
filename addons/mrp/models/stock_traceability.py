from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockTraceabilityReport(models.TransientModel):
    _inherit = "stock.traceability.report"

    @api.model
    def _get_models_allowed_line(self):
        return super()._get_models_allowed_line() | {"mrp.production", "mrp.unbuild"}

    @api.model
    def _get_reference(self, move_line):
        res_model, res_id, ref = super()._get_reference(move_line)
        if (
            move_line.move_id.production_id
            and move_line.move_id.location_dest_usage != "inventory"
        ):
            res_model = "mrp.production"
            res_id = move_line.move_id.production_id.id
            ref = move_line.move_id.production_id.name
        if (
            move_line.move_id.raw_material_production_id
            and move_line.move_id.location_dest_usage != "inventory"
        ):
            res_model = "mrp.production"
            res_id = move_line.move_id.raw_material_production_id.id
            ref = move_line.move_id.raw_material_production_id.name
        if move_line.move_id.unbuild_id:
            res_model = "mrp.unbuild"
            res_id = move_line.move_id.unbuild_id.id
            ref = move_line.move_id.unbuild_id.name
        if move_line.move_id.consume_unbuild_id:
            res_model = "mrp.unbuild"
            res_id = move_line.move_id.consume_unbuild_id.id
            ref = move_line.move_id.consume_unbuild_id.name
        _debug.logic(
            "traceability_reference",
            move_line=move_line.id,
            res_model=res_model,
            res_id=res_id,
        )
        return res_model, res_id, ref

    @api.model
    def _get_linked_move_lines(self, move_line):
        move_lines, is_used = super()._get_linked_move_lines(move_line)
        if not move_lines:
            move_lines = (
                move_line.move_id.consume_unbuild_id and move_line.produce_line_ids
            ) or (move_line.move_id.production_id and move_line.consume_line_ids)
        if not is_used:
            is_used = (move_line.move_id.unbuild_id and move_line.consume_line_ids) or (
                move_line.move_id.raw_material_production_id
                and move_line.produce_line_ids
            )
        return move_lines, is_used
