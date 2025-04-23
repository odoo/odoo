# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields


class EventSlot(models.Model):
    _name = 'event.slot'
    _inherit = ['event.slot', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [
            ('event_id.is_finished', '=', False),
            ('event_id.company_id', '=', data['pos.config'][0]['company_id']),
            ('event_id', 'in', [event['id'] for event in data['event.event']]),
            ('start_datetime', '>=', fields.Datetime.now()),
        ]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'date', 'display_name', 'event_id', 'registration_ids', 'seats_available', 'start_datetime']
