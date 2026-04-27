# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockRequestCount(models.TransientModel):
    _inherit = 'stock.request.count'

    def _get_quants_to_count(self):
        quants_to_count = super()._get_quants_to_count()
        if self.env.user.has_group('stock_barcode.group_barcode_count_entire_location'):
            location_ids = self.quant_ids.location_id.ids
            quants_to_count = self.env['stock.quant'].search([('location_id', 'in', location_ids)])
        return quants_to_count
