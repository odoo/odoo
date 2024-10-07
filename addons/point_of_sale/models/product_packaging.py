from odoo import api, models
from odoo.osv.expression import AND


class ProductPackaging(models.Model):
    _inherit = ['product.packaging', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return AND([[('barcode', 'not in', ['', False])], [('product_id', 'in', [x['id'] for x in data['product.product']['data']])] if data else []])

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'barcode', 'product_id', 'qty']
