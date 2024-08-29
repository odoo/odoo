from odoo import api, models
from odoo.addons import product


class ProductProduct(models.Model, product.ProductProduct):

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result.append('all_product_tag_ids')
        return result
