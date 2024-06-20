# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductComboLine(models.Model):
    _name = 'product.combo.line'
    _inherit = ['product.combo.line', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', list(set().union(*[combo.get('combo_line_ids') for combo in data['product.combo']['data']])))]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'combo_id', 'product_id', 'extra_price']
