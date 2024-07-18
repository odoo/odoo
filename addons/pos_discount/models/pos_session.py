# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_data(self, models_to_load, only_data=False):
        result = super().load_data(models_to_load, only_data)

        # adapt product
        if len(models_to_load) == 0 or 'product.product' in models_to_load:
            product_params = self._load_data_params(self.config_id)['product.product']
            discount_product_id = self.config_id.discount_product_id.id
            product_ids_set = {product['id'] for product in result['data']['product.product']}

            if self.config_id.module_pos_discount and discount_product_id not in product_ids_set:
                productModel = self.env['product.product'].with_context(**product_params['context'])
                product = productModel.search_read([('id', '=', discount_product_id)], fields=product_params['fields'], load=False)
                self._process_pos_ui_product_product(product)
                result['data']['product.product'].extend(product)

        return result
