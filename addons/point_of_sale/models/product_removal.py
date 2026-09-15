# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class ProductRemoval(models.Model):
    _name = 'product.removal'
    _inherit = ['product.removal', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['method']
