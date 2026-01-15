# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _get_proc_values(self, line):
        sol = line.move_id.sale_line_id
        if sol:
            return sol._prepare_procurement_values()
        return super()._get_proc_values(line)
