# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _load_pos_self_data_fields(self, pos_config_id):
        return super()._load_pos_self_data_fields(pos_config_id) + ['module_pos_deposit']
