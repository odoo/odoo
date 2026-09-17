from uuid import uuid4

from odoo import _, api, fields, models
from odoo.fields import Domain

from .resource_asset import ROOM_KIND

BOOKABLE_BACKGROUND_COLOR = "#83c5be"
BOOKED_BACKGROUND_COLOR = "#dd2d4a"


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    short_code = fields.Char(copy=False)
    access_token = fields.Char(
        copy=False,
        readonly=True,
    )
    room_booking_url = fields.Char(
        string="Room Link",
        compute="_compute_room_booking_url",
    )
    bookable_background_color = fields.Char(string="Available Background Color")
    booked_background_color = fields.Char()
    room_background_image = fields.Image(string="Background Image")
    is_available = fields.Boolean(
        string="Is Currently Available",
        compute="_compute_booking_status",
    )
    next_booking_start = fields.Datetime(compute="_compute_booking_status")

    _uniq_access_token = models.Constraint(
        "unique(access_token)",
        "The access token must be unique",
    )
    _uniq_short_code = models.Constraint(
        "unique(short_code)",
        "The short code must be unique.",
    )

    @api.depends("short_code")
    def _compute_room_booking_url(self):
        for room in self:
            room.room_booking_url = (
                room.short_code
                and f"{room.get_base_url()}/room/{room.short_code}/book"
            )

    @api.depends(
        "reservation_ids.date_start",
        "reservation_ids.date_end",
        "reservation_ids.allocated_percentage",
        "reservation_ids.active",
    )
    def _compute_booking_status(self):
        now = fields.Datetime.now()
        reservations = (
            self.env["resource.reservation"]
            .sudo()
            .search_fetch(
                [
                    ("resource_id", "in", self.ids),
                    ("active", "=", True),
                    ("allocated_percentage", ">", 0),
                    ("date_end", ">", now),
                ],
                ["resource_id", "date_start"],
                order="date_start",
            )
        )
        busy = set()
        next_start = {}
        for reservation in reservations:
            resource_id = reservation.resource_id.id
            if reservation.date_start <= now:
                busy.add(resource_id)
            else:
                next_start.setdefault(resource_id, reservation.date_start)
        for room in self:
            room.is_available = room.id not in busy
            room.next_booking_start = next_start.get(room.id)

    def write(self, vals):
        res = super().write(vals)
        kiosk_fields = {
            "short_code",
            "bookable_background_color",
            "booked_background_color",
            "room_background_image",
            "description",
            "name",
            "active",
        }
        if kiosk_fields & vals.keys():
            for room in self.filtered("access_token"):
                room._notify_booking_view("reload")
        return res

    def _setup_room_kiosk(self):
        rooms = self.filtered(
            lambda resource: resource.sudo().asset_id.kind_id.code == ROOM_KIND
        )
        room_type = self.env.ref("room.appointment_type_room", raise_if_not_found=False)
        for room in rooms.sudo():
            vals = {}
            if not room.short_code:
                vals["short_code"] = str(uuid4())[:8]
            if not room.access_token:
                vals["access_token"] = str(uuid4())
            if not room.bookable_background_color:
                vals["bookable_background_color"] = BOOKABLE_BACKGROUND_COLOR
            if not room.enforce_booking_limit:
                vals["enforce_booking_limit"] = True
            if not room.booked_background_color:
                vals["booked_background_color"] = BOOKED_BACKGROUND_COLOR
            if room_type and room_type not in room.appointment_type_ids:
                vals["appointment_type_ids"] = [fields.Command.link(room_type.id)]
            if vals:
                super(ResourceResource, room).write(vals)

    def _get_room_bookings(self, domain=None):
        self.check_singleton()
        return (
            self.env["calendar.event"]
            .sudo()
            .search(
                Domain("booking_line_ids.resource_id", "=", self.id)
                & Domain(domain or []),
                order="start asc",
            )
        )

    def _get_room_blocks(self, since):
        self.check_singleton()
        return (
            self.env["resource.reservation"]
            .sudo()
            .search(
                [
                    ("resource_id", "=", self.id),
                    ("active", "=", True),
                    ("allocated_percentage", ">", 0),
                    ("date_end", ">", since),
                    ("res_model", "!=", "calendar.event"),
                ],
                order="date_start asc",
            )
        )

    def action_view_booking_view(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "url": self.room_booking_url,
            "target": "new",
        }

    def action_view_bookings(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "room.room_booking_action"
        )
        action["domain"] = [("resource_ids", "in", self.ids)]
        action["context"] = {
            "default_appointment_type_id": self.env.ref(
                "room.appointment_type_room"
            ).id,
            "default_resource_ids": self.ids if len(self) == 1 else [],
        }
        action["name"] = _("Bookings")
        return action

    def _notify_booking_view(self, method, events=False):
        self.check_singleton()
        if not self.access_token:
            return
        channel = f"room_booking#{self.access_token}"
        if method == "reload":
            self.env["bus.bus"]._sendone(
                channel, f"room#{self.id}/reload", self.room_booking_url
            )
        elif method in ("create", "delete", "update"):
            self.env["bus.bus"]._sendone(
                channel,
                f"room#{self.id}/booking/{method}",
                [event._get_room_booking_values() for event in (events or [])],
            )
        else:
            raise NotImplementedError(
                f"Method '{method}' is not implemented for '_notify_booking_view'"
            )
