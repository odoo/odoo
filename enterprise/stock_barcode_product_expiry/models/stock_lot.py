# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model
    def _get_fields_stock_barcode(self):
        return super()._get_fields_stock_barcode() + ['expiration_date']
