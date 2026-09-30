# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class EventQuestion(models.Model):
    _name = 'event.question'
    _inherit = ['event.question', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['title', 'question_type', 'event_type_ids', 'event_ids', 'sequence', 'once_per_order', 'is_mandatory_answer', 'answer_ids']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('event_ids', 'in', [event['id'] for event in data['event.event']])]
