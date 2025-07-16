# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _load_self_data_models(self):
        return super()._load_self_data_models() + ['event.event.ticket', 'event.event', 'event.slot', 'event.registration', 'event.question', 'event.question.answer', 'event.registration.answer']
