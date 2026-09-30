# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductComboItem(models.Model):
    _name = 'product.combo.item'
    _inherit = ['product.combo.item', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', list(set().union(*[combo.get('combo_item_ids') for combo in data['product.combo']])))]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'combo_id', 'product_id', 'extra_price', 'currency_id']

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        self._convert_pos_data_currency(read_records, config, 'extra_price', 'currency_id')
        return read_records
