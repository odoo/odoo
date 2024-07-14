# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_stock_barcode_data(self):
        data = super()._get_stock_barcode_data()
        kit_boms = self.move_ids.bom_line_id.bom_id.filtered(lambda bom: bom.type == 'phantom')
        if kit_boms:
            packagings = (
                kit_boms.mapped('product_id.packaging_ids') or
                kit_boms.mapped('product_tmpl_id.packaging_ids')
            )
            data['records']['product.packaging'] += packagings.read(packagings._get_fields_stock_barcode(), load=False)

        return data
