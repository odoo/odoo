from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def bulk_stock_move_line_cancel(self):
        """this method used to sales order confirmation in bulk."""
        for stock_move in self:
            stock_move.update({'state': 'cancel'})

    def bulk_stock_move_line_cancel_reset(self):
        """this method used to sales order confirmation in bulk."""
        for stock_move in self:
            stock_move.update({'state': 'draft'})
