# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _get_dynamic_models(self):
        models = super()._get_dynamic_models()
        return models + ['event.registration', 'event.registration.answer']

    def _update_events_seats(self, events):
        data = []
        for event in events:
            data.append({
                'event_id': event.id,
                'seats_available': event.seats_available,
                'event_ticket_ids': [{
                    'ticket_id': ticket.id,
                    'seats_available': ticket.seats_available
                } for ticket in event.event_ticket_ids]
            })

        for record in self:
            record._notify('UPDATE_AVAILABLE_SEATS', data)
