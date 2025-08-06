from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_data(self, data):
        # Deprecated
        # Kept for backward compatibility.
        res = super()._load_pos_data(data)
        config_id = self.env['pos.config'].browse(data['pos.config'][0]['id'])
        discount_product_id = config_id.discount_product_id.product_tmpl_id.id
        product_ids_set = {product['id'] for product in res}

        if config_id.module_pos_discount and discount_product_id not in product_ids_set:
            productModel = self.env['product.template'].with_context({**self.env.context, 'display_default_code': False})
            fields = self.env['product.template']._load_pos_data_fields(data['pos.config'][0]['id'])
            product = productModel.search_read([('id', '=', discount_product_id)], fields=fields, load=False)
            res.extend(product)

        return res

    def _load_pos_metadata(self, data, search_params={}):
        super()._load_pos_metadata(data, search_params)
        config_id = data['pos.config']['records'][0]
        discount_product_id = config_id.discount_product_id.product_tmpl_id

        if config_id.module_pos_discount:
            data['product.template']['records'] |= discount_product_id

        return data
