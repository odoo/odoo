# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_pos_ui_product_product(self, params):
        result = super()._get_pos_ui_product_product(params)
        discount_product_id = self.config_id.discount_product_id.id
        product_ids_set = {product['id'] for product in result}

        if self.config_id.module_pos_discount and discount_product_id not in product_ids_set:
            productModel = self.env['product.product'].with_context(**params['context'])
            product = productModel.search_read([('id', '=', discount_product_id)], fields=params['search_params']['fields'])
            self._process_pos_ui_product_product(product)
            result.extend(product)
        return result
