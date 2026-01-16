from datetime import datetime

from odoo import models


class EventSlot(models.Model):
    _inherit = "event.slot"

    def _filter_open_slots(self):
        return self.filtered(
            lambda slot: slot.start_datetime > datetime.now()
            and any(
                availability is None or availability > 0
                for availability in slot.event_id._get_seats_availability([
                    (slot, ticket) for ticket in slot.event_id.event_ticket_ids or [False]
                ])
            )
        )
