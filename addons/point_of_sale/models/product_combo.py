# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductCombo(models.Model):
    _name = 'product.combo'
    _inherit = ['product.combo', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        combo_ids = data['product.template'].combo_ids.ids
        return [('id', 'in', combo_ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.combo.item']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'combo_item_ids', 'base_price']
