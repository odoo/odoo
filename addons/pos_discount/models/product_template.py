from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_metadata(self, data, search_params={}):
        super()._load_pos_metadata(data, search_params)
        config_id = data['pos.config']['records'][0]
        discount_product_id = config_id.discount_product_id.product_tmpl_id

        if config_id.module_pos_discount:
            data['product.template']['records'] |= discount_product_id

        return data
