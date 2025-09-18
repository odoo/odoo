from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def _get_proc_values(self, line):
        sol = line.move_id.sale_line_id
        if sol:
            return sol._prepare_procurement_vals()
        return super()._get_proc_values(line)
