from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['invoice_policy', 'type', 'sale_line_warn', 'sale_line_warn_msg']
        return params
