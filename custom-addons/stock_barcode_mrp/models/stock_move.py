
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_fields_stock_barcode(self):
        return [
            'product_id',
            'location_id',
            'product_uom_qty',
            'move_line_ids',
            'product_uom',
        ]
