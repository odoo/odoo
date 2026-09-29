from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        vals = super()._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        if self.repair_id:
            vals['repair_id'] = self.repair_id.id
        return vals

    def _prepare_phantom_line_vals(self, bom_line, qty):
        self.ensure_one()
        product = bom_line.product_id
        return {
            'repair_id': self.repair_id.id,
            'repair_line_type': self.repair_line_type,
            'product_id': product.id,
            'price_unit': self.price_unit,
            'product_uom_qty': qty,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'state': 'draft',
        }
