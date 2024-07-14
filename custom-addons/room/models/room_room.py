# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4

from odoo import api, fields, models, _
from odoo.tools.translate import html_translate

class Room(models.Model):
    _name = "room.room"
    _inherit = ["mail.thread"]
    _description = "Room"
    _order = "name, id"

    # Configuration
    name = fields.Char(string="Room Name", required=True, tracking=2)
    description = fields.Html(string="Amenities", translate=html_translate)
    office_id = fields.Many2one("room.office", string="Office", required=True, tracking=3)
    company_id = fields.Many2one(related="office_id.company_id", string="Company", store=True)
    room_booking_ids = fields.One2many("room.booking", "room_id", string="Bookings")
    short_code = fields.Char("Short Code", default=lambda self: str(uuid4())[:8], copy=False, required=True, tracking=1)
    # Technical/Statistics
    access_token = fields.Char("Access Token", default=lambda self: str(uuid4()), copy=False, readonly=True, required=True)
    bookings_count = fields.Integer("Bookings Count", compute="_compute_bookings_count")
    is_available = fields.Boolean(string="Is Room Currently Available", compute="_compute_is_available")
    next_booking_start = fields.Datetime("Next Booking Start", compute="_compute_next_booking_start")
    room_booking_url = fields.Char("Room Booking URL", compute="_compute_room_booking_url")
    # Frontend design fields
    bookable_background_color = fields.Char("Available Background Color", default="#83c5be")
    booked_background_color = fields.Char("Booked Background Color", default="#dd2d4a")
    room_background_image = fields.Image("Background Image")

    _sql_constraints = [
        ("uniq_access_token", "unique(access_token)", "The access token must be unique"),
        ("uniq_short_code", "unique(short_code)", "The short code must be unique."),
    ]

    @api.depends("room_booking_ids")
    def _compute_bookings_count(self):
        bookings_count_by_room = dict(self.env["room.booking"]._read_group(
            [("stop_datetime", ">=", fields.Datetime.now()), ("room_id", "in", self.ids)],
            ["room_id"],
            ["__count"]
        ))
        for room in self:
            room.bookings_count = bookings_count_by_room.get(room, 0)

    @api.depends("office_id")
    def _compute_display_name(self):
        super()._compute_display_name()
        for room in self:
            room.display_name = f"{room.office_id.name} - {room.name}"

    @api.depends("room_booking_ids")
    def _compute_is_available(self):
        now = fields.Datetime.now()
        booked_rooms = {room.id for room, in self.env["room.booking"]._read_group(
            [("start_datetime", "<=", now), ("stop_datetime", ">=", now), ("room_id", "in", self.ids)],
            ["room_id"],
        )}
        for room in self:
            room.is_available = room.id not in booked_rooms

    @api.depends("is_available", "room_booking_ids")
    def _compute_next_booking_start(self):
        now = fields.Datetime.now()
        next_booking_start_by_room = dict(self.env["room.booking"]._read_group(
            [("start_datetime", ">", now), ("room_id", "in", self.filtered('is_available').ids)],
            ["room_id"],
            ["start_datetime:min"],
        ))
        for room in self:
            room.next_booking_start = next_booking_start_by_room.get(room)

    @api.depends("short_code")
    def _compute_room_booking_url(self):
        for room in self:
            room.room_booking_url = f"{room.get_base_url()}/room/{room.short_code}/book"

    # ------------------------------------------------------
    # CRUD / ORM
    # ------------------------------------------------------

    def write(self, vals):
        result = super(Room, self).write(vals)
        for room in self:
            room._notify_booking_view("reload")
        return result

    # ------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------

    def action_open_booking_view(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.room_booking_url,
            "target": "new",
        }

    def action_view_bookings(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "room.booking",
            "name": _("Bookings"),
            "domain": [("room_id", "in", self.ids)],
            "context": {"default_room_id": self.id if len(self) == 1 else False},
            "view_mode": "calendar,gantt,kanban,tree,form",
        }

    # ------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------

    def _notify_booking_view(self, method, bookings=False):
        """The room booking page is meant to be used on a 'static' device (such
        as a tablet) and is not expected to be reloaded manually. We thus need
        a way to notify the frontend page of any change inside the room
        configuration (in which case we reload the view to apply those changes)
        or any booking update.
        """
        self.ensure_one()
        if method == "reload":
            self.env["bus.bus"]._sendone(f"room_booking#{self.access_token}", "reload", self.room_booking_url)
        elif method in ["create", "delete", "update"]:
            self.env["bus.bus"]._sendone(
                f"room_booking#{self.access_token}",
                f"booking/{method}",
                [{
                    "id": booking.id,
                    "name": booking.name,
                    "start_datetime": booking.start_datetime,
                    "stop_datetime": booking.stop_datetime,
                } for booking in (bookings or [])]
            )
        else:
            raise NotImplementedError(f"Method '{method}' is not implemented for '_notify_booking_view'")
