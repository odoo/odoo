from odoo import models, api

class MrpStockReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def _get_reference(self, move_line):
        res_model, res_id, ref = super(MrpStockReport, self)._get_reference(move_line)
        if move_line.move_id.production_id and not move_line.move_id.production_id.unbuild and not move_line.move_id.scrapped:
            res_model = 'mrp.production'
            res_id = move_line.move_id.production_id.id
            ref = move_line.move_id.production_id.name
        if move_line.move_id.raw_material_production_id and not move_line.move_id.raw_material_production_id.unbuild and not move_line.move_id.scrapped:
            res_model = 'mrp.production'
            res_id = move_line.move_id.raw_material_production_id.id
            ref = move_line.move_id.raw_material_production_id.name
        if move_line.move_id.raw_material_production_id.unbuild:
            res_model = 'mrp.production'
            res_id = move_line.move_id.raw_material_production_id.id
            ref = move_line.move_id.raw_material_production_id.name
        if move_line.move_id.production_id.unbuild:
            res_model = 'mrp.production'
            res_id = move_line.move_id.production_id.id
            ref = move_line.move_id.production_id.name
        return res_model, res_id, ref

    @api.model
    def _get_linked_move_lines(self, move_line):
        move_lines, is_used = super(MrpStockReport, self)._get_linked_move_lines(move_line)
        if not move_lines:
            move_lines = (move_line.move_id.production_id.unbuild and move_line.produce_line_ids) or (move_line.move_id.production_id and move_line.consume_line_ids)
        if not is_used:
            is_used = (move_line.move_id.raw_material_production_id.unbuild and move_line.consume_line_ids) or (move_line.move_id.raw_material_production_id and move_line.produce_line_ids)
        return move_lines, is_used
