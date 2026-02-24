# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _get_proc_values(self, line):
        proc_values = super()._get_proc_values(line)
        proc_values['bom_line_id'] = line.move_id.bom_line_id.id
        return proc_values
