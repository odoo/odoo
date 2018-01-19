from odoo import models, api

class MrpStockReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def _get_reference(self, move_line):
        res_model, res_id, ref = super(MrpStockReport, self)._get_reference(move_line)
        if move_line.move_id.repair_id:
            res_model = 'repair.order'
            res_id = move_line.move_id.repair_id.id
            ref = move_line.move_id.repair_id.name
        return res_model, res_id, ref

    @api.model
    def _get_linked_move_lines(self, move_line):
        move_lines, is_used = super(MrpStockReport, self)._get_linked_move_lines(move_line)
        if not move_lines:
            move_lines = move_line.move_id.repair_id and move_line.consume_line_ids
        if not is_used:
            is_used = move_line.move_id.repair_id and move_line.produce_line_ids
        return move_lines, is_used
