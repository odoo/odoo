from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_self_data_search_read(self, data, config):
        read_data = super()._load_pos_self_data_search_read(data, config)

        fields = self.env['product.template']._load_pos_self_data_fields(config)
        missing_product_templates = self._get_loyalty_product_to_load(data, config, read_data, fields, False)

        read_data.extend(missing_product_templates)
        return read_data
