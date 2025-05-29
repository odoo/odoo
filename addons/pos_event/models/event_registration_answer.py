# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from uuid import uuid4


class EventRegistrationAnswer(models.Model):
    _name = 'event.registration.answer'
    _inherit = ['event.registration.answer', 'pos.load.mixin']

    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['question_id', 'registration_id', 'value_answer_id', 'value_text_box', 'partner_id',
                'write_date', 'event_id', 'uuid']

    @api.model
    def _load_pos_data_domain(self, data):
        return False
