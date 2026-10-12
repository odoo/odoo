# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model
    def _load_pos_data_fields(self, config):
        pos_data_fields = super()._load_pos_data_fields(config)
        pos_data_fields.append('removal_strategy_id')
        return pos_data_fields
