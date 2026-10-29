from datetime import datetime

from odoo import models


class EventSlot(models.Model):
    _inherit = "event.slot"

    def _filter_open_slots(self):
        future_slots = self.filtered(lambda slot: slot.start_datetime > datetime.now())
        open_slot_ids = set()

        for event, slots in future_slots.grouped('event_id').items():
            slot_tickets = [(slot, ticket) for slot in slots for ticket in event.event_ticket_ids or [False]]
            availabilities = event._get_seats_availability(slot_tickets)
            open_slot_ids.update(
                slot.id
                for (slot, _), availability in zip(slot_tickets, availabilities)
                if availability is None or availability > 0
            )

        return future_slots.filtered(lambda slot: slot.id in open_slot_ids)
