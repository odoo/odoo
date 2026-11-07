# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_self_metadata(self, data, search_params={}):
        data = super()._load_pos_self_metadata(data, search_params)
        products = data['product.template']['records']
        data['product.template']['records'] = products | products.deposit_product_id.product_tmpl_id
        return data
