from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_read(self, records, config):
        read_data = super()._load_pos_data_read(records, config)
        discount_product_id = config.discount_product_id.id
        product_ids_set = {product['id'] for product in read_data}

        if config.module_pos_discount and discount_product_id not in product_ids_set:
            product_model = self.env['product.product'].with_context({**self.env.context, 'display_default_code': False})
            records = product_model.search([('id', '=', discount_product_id)])
            read_records = self._load_pos_data_read(records, config)
            read_data.extend(read_records)

        return read_data
