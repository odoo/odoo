from odoo import api, models
from odoo.osv.expression import OR


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_domain(self, data):
        params = super()._load_pos_data_domain(data)
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        if config_id.module_pos_discount:
            params = OR([params, [('id', '=', config_id.discount_product_id.id)]])
        return params
