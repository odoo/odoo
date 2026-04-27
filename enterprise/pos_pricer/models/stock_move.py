import logging

from odoo import models


_logger = logging.getLogger(__name__)


class PricerStockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals.get('state') == 'done':
            self.mapped('product_id').sudo().write({'pricer_product_to_create_or_update': True})
        return res
