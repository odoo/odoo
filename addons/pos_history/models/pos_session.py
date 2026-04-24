# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        # loaded the models and fields but will store data only when is_history_tracked is enabled.
        data += ['pos.history.line']
        return data
