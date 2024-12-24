# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _get_proc_values(self, line):
        vals = super()._get_proc_values(line)
        vals['sale_line_id'] = line.move_id.sale_line_id.id
        return vals
