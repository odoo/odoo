from odoo import models, api


class StockTraceabilityReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def _get_reference(self, move_line):
        res_model, res_id, ref = super()._get_reference(move_line)
        if move_line.move_id.production_id and move_line.move_id.location_dest_usage != 'inventory':
            res_model = 'mrp.production'
            res_id = move_line.move_id.production_id.id
            ref = move_line.move_id.production_id.name
        if move_line.move_id.raw_material_production_id and move_line.move_id.location_dest_usage != 'inventory':
            res_model = 'mrp.production'
            res_id = move_line.move_id.raw_material_production_id.id
            ref = move_line.move_id.raw_material_production_id.name
        if move_line.move_id.unbuild_id:
            res_model = 'mrp.unbuild'
            res_id = move_line.move_id.unbuild_id.id
            ref = move_line.move_id.unbuild_id.name
        if move_line.move_id.consume_unbuild_id:
            res_model = 'mrp.unbuild'
            res_id = move_line.move_id.consume_unbuild_id.id
            ref = move_line.move_id.consume_unbuild_id.name
        return res_model, res_id, ref

    @api.model
    def _get_linked_move_lines(self, move_line):
        """ Return all the move lines linked to move_line.
        parent_lines are the move lines that happen first in the production chain. We go towards the raw components.
        children_lines are the move lines that happen later in the production chain. We go towards the final products. """
        parent_lines, children_lines = super()._get_linked_move_lines(move_line)
        if not parent_lines:
            parent_lines = (move_line.move_id.consume_unbuild_id and move_line.produce_line_ids) or (move_line.move_id.production_id and move_line.consume_line_ids)
        if not children_lines:
            children_lines = (move_line.move_id.unbuild_id and move_line.consume_line_ids) or (move_line.move_id.raw_material_production_id and move_line.produce_line_ids)
        return parent_lines, children_lines
