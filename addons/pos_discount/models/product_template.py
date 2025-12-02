from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_read(self, records, config):
        read_data = super()._load_pos_data_read(records, config)
        discount_product_id = config.discount_product_id.id
        product_ids_set = {product['id'] for product in read_data}

        if config.module_pos_discount and discount_product_id not in product_ids_set:
            productModel = self.env['product.template'].with_context({**self.env.context, 'display_default_code': False})
            fields = self.env['product.template']._load_pos_data_fields(config)
            product = productModel.search_read([('id', '=', discount_product_id)], fields=fields, load=False)
            read_data.extend(product)

        return read_data
