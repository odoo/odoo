# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        models = super()._load_pos_data_models(config_id)
        models += ['event.event.ticket', 'event.event', 'event.registration', 'event.question', 'event.question.answer', 'event.registration.answer']
        return models
