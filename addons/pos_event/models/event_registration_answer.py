# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class EventRegistrationAnswer(models.Model):
    _name = 'event.registration.answer'
    _inherit = ['event.registration.answer', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['question_id', 'registration_id', 'value_answer_id', 'value_text_box', 'partner_id', 'event_id']

    @api.model
    def _load_pos_data_domain(self, data):
        return False
