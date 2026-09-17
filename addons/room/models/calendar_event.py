from odoo import api, fields, models

KIOSK_EVENT_FIELDS = {"name", "start", "stop", "active"}


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _get_room_booking_values(self):
        self.check_singleton()
        return {
            "id": self.id,
            "name": self.name,
            "start_datetime": fields.Datetime.to_string(self.start),
            "stop_datetime": fields.Datetime.to_string(self.stop),
        }

    def _get_kiosk_rooms(self):
        return self.sudo().booking_line_ids.resource_id.filtered(
            "access_token"
        )

    def _notify_room_kiosks(self, method):
        for room in self._get_kiosk_rooms():
            events = self.filtered(
                lambda event, room=room: (
                    room in event.sudo().booking_line_ids.resource_id
                )
            )
            room._notify_booking_view(method, events)

    def write(self, vals):
        if not KIOSK_EVENT_FIELDS & vals.keys():
            return super().write(vals)
        rooms_before = {event.id: event._get_kiosk_rooms() for event in self}
        res = super().write(vals)
        for event in self:
            rooms_now = event._get_kiosk_rooms()
            if not event.active:
                rooms_now = rooms_now.browse()
            for room in rooms_before[event.id] - rooms_now:
                room._notify_booking_view("delete", event)
            for room in rooms_now:
                room._notify_booking_view("update", event)
        return res

    def unlink(self):
        self._notify_room_kiosks("delete")
        return super().unlink()

    @api.model
    def _create_room_booking(self, room, name, start, stop):
        return (
            self.sudo()
            .with_context(no_mail_to_attendees=True, mail_create_nosubscribe=True)
            .create(
                {
                    "name": name,
                    "start": start,
                    "stop": stop,
                    "user_id": False,
                    "partner_ids": [],
                    "appointment_type_id": self.env.ref(
                        "room.appointment_type_room"
                    ).id,
                    "booking_line_ids": [
                        fields.Command.create(
                            {"resource_id": room.id, "capacity_reserved": 1}
                        )
                    ],
                }
            )
        )
