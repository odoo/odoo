from odoo import models, api

class MrpStockReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def get_links(self, move_line):
        res_model, res_id, ref = super(MrpStockReport, self).get_links(move_line)
        if move_line.production_id:
            res_model = 'mrp.production'
            res_id = move_line.production_id.id
            ref = move_line.production_id.name
        if move_line.move_id.unbuild_id:
            res_model = 'mrp.unbuild'
            res_id = move_line.move_id.unbuild_id.id
            ref = move_line.move_id.unbuild_id.name
        if move_line.move_id.consume_unbuild_id:
            res_model = 'mrp.unbuild'
            res_id = move_line.move_id.consume_unbuild_id.id
            ref = move_line.move_id.consume_unbuild_id.name
        return res_model, res_id, ref
