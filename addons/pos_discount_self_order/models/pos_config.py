# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _load_pos_self_data_fields(self, config):
        return super()._load_pos_self_data_fields(config) + ['discount_product_id']
