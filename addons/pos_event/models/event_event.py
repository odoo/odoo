from odoo import api, fields, models


class EventEvent(models.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'pos.load.mixin']

    image_1024 = fields.Image("PoS Image", max_width=1024, max_height=1024)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('event_ticket_ids', 'in', [ticket['id'] for ticket in data['event.event.ticket']])]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'seats_available', 'event_ticket_ids', 'registration_ids', 'seats_limited', 'write_date',
                'question_ids', 'general_question_ids', 'specific_question_ids', 'seats_max',
                'is_multi_slots', 'event_slot_ids']

    def get_slot_tickets_availability_pos(self, slot_ticket_ids):
        self.ensure_one()
        slot_tickets = [
            (
                self.event_slot_ids.filtered(lambda slot: slot.id == slot_id) if slot_id else self.env['event.slot'],
                self.event_ticket_ids.filtered(lambda ticket: ticket.id == ticket_id) if ticket_id else self.env['event.event.ticket']
            )
            for slot_id, ticket_id in slot_ticket_ids
        ]
        return self._get_seats_availability(slot_tickets)
