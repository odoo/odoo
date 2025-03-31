from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _load_pos_data(self, data):
        res = super()._load_pos_data(data)
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        discount_product_id = config_id.discount_product_id.id
        product_ids_set = {product['id'] for product in res['data']}

        if config_id.module_pos_discount and discount_product_id not in product_ids_set:
            productModel = self.env['product.product'].with_context({**self.env.context, 'display_default_code': False})
            product = productModel.search_read([('id', '=', discount_product_id)], fields=res['fields'], load=False)
            self._process_pos_ui_product_product(product, config_id)
            res['data'].extend(product)

        return res
