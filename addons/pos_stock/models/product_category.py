from odoo import api, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        fields.append('removal_strategy_id')
        return fields
