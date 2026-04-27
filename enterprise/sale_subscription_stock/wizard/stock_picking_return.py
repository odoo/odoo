# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    def _prepare_move_default_values(self, new_picking):
        vals = super()._prepare_move_default_values(new_picking)
        # copy the deadline from the original move so the return counts as an incoming move
        # for the subscription period
        if self.move_id.sale_line_id.recurring_invoice:
            vals['date_deadline'] = self.move_id.date_deadline
        return vals
