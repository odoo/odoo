# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        data += ['fidelity.program', 'fidelity.rule', 'fidelity.reward', 'fidelity.card', 'fidelity.balance', 'fidelity.transaction']
        return data
