# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_stock_barcode_data(self):
        data = super()._get_stock_barcode_data()
        kit_boms = self.move_ids.bom_line_id.bom_id.filtered(lambda bom: bom.type == 'phantom')
        if kit_boms:
            data_product_ids = {product['id'] for product in data['records']['product.product']}
            data_packaging_ids = {packaging['id'] for packaging in data['records']['product.packaging']}
            kit_variants = kit_boms.product_tmpl_id.product_variant_ids.filtered(lambda prod: prod.id not in data_product_ids)
            packagings = kit_variants.packaging_ids.filtered(lambda pack: pack.id not in data_packaging_ids)
            data['records']['product.product'] += kit_variants.read(self.env['product.product']._get_fields_stock_barcode(), load=False)
            data['records']['product.packaging'] += packagings.read(self.env['product.packaging']._get_fields_stock_barcode(), load=False)

        return data
