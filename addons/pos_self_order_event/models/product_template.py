# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_self_data_fields(self, config):
        return super()._load_pos_self_data_fields(config) + ['self_order_visible']
