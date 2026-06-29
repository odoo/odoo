from odoo import api,models

class ProductProduct(models.Model):

    _inherit = "product.product"

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += ['public_description']
        return fields
