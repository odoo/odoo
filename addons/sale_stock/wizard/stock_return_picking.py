# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _get_proc_values(self, line):
        sol = line.move_id.sale_line_id
        if sol:
            return sol._prepare_procurement_values(group_id=self.picking_id.group_id)
        return super()._get_proc_values(line)
