from odoo import models, api

class MrpStockReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def get_links(self, move_line):
        res_model, res_id, ref = super(MrpStockReport, self).get_links(move_line)
        if move_line.move_id.repair_id:
            res_model = 'repair.order'
            res_id = move_line.move_id.repair_id.id
            ref = move_line.move_id.repair_id.name
        return res_model, res_id, ref
