
from odoo import api, models


class ProductUom(models.Model):
    _name = 'product.uom'
    _inherit = ['product.uom', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'barcode', 'product_id', 'uom_id']

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config'][0]['id'])
        return self.with_context({**self.env.context}).search_read(domain, fields, load=False)
