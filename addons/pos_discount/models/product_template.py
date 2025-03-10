from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_data(self, data):
        res = super()._load_pos_data(data)
        config_id = self.env['pos.config'].browse(data['pos.config'][0]['id'])
        discount_product_id = config_id.discount_product_id.id
        product_ids_set = {product['id'] for product in res}

        if config_id.module_pos_discount and discount_product_id not in product_ids_set:
            productModel = self.env['product.product'].with_context({**self.env.context, 'display_default_code': False})
            fields = self.env['product.template']._load_pos_data_fields(data['pos.config'][0]['id'])
            product = productModel.search_read([('id', '=', discount_product_id)], fields=fields, load=False)
            res.extend(product)

        return res
