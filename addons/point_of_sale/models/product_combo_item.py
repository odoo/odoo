# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import product, point_of_sale

from odoo import api, models


class ProductComboItem(models.Model, product.ProductComboItem, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', list(set().union(*[combo.get('combo_item_ids') for combo in data['product.combo']['data']])))]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'combo_id', 'product_id', 'extra_price']
