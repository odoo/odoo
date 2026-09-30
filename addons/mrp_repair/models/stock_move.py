from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        vals = super()._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        if self.repair_id:
            vals['repair_id'] = self.repair_id.id
        return vals
