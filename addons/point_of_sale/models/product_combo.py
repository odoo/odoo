# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons import point_of_sale, product


class ProductCombo(product.ProductCombo, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', list(set().union(*[product.get('combo_ids') for product in data['product.product']['data']])))]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'combo_item_ids', 'base_price']
