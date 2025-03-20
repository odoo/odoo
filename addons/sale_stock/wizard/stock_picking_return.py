# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    def _prepare_move_default_values(self, new_picking):
        vals = super()._prepare_move_default_values(new_picking)
        if self.move_id.sale_line_id:
            vals['sale_line_id'] = self.move_id.sale_line_id
        return vals


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _prepare_picking_default_values_based_on(self, picking):
        vals = super()._prepare_picking_default_values_based_on(picking)
        if picking.sale_id:
            vals['sale_id'] = picking.sale_id.id
        return vals
