from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _should_ignore_backorders(self):
        return super()._should_ignore_backorders() and not any(move.sale_line_id.is_rental for move in self.move_ids)
