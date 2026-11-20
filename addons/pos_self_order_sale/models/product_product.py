# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _load_pos_self_data_fields(self, config_id):
        fields = super()._load_pos_self_data_fields(config_id)
        fields += ["optional_product_ids"]
        return fields
