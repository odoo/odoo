
from odoo import api, models


class ProductUom(models.Model):
    _name = 'product.uom'
    _inherit = ['product.uom', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'barcode', 'product_id', 'uom_id']
