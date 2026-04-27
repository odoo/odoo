# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class RoomBooking(models.Model):
    _name = "room.booking"
    _inherit = ["mail.thread"]
    _description = "Room Booking"
    _order = "start_datetime desc, id"

    name = fields.Char(string="Booking Name", required=True, tracking=1)
    room_id = fields.Many2one("room.room", string="Room", required=True, ondelete="cascade", group_expand="_read_group_room_id", tracking=4)
    start_datetime = fields.Datetime(string="Start Datetime", required=True, tracking=2)
    stop_datetime = fields.Datetime(string="End Datetime", required=True, tracking=3)
    organizer_id = fields.Many2one("res.users", string="Organizer", default=lambda self: self.env.user.id if not self.env.user._is_public() else False, tracking=5)

    # Fields used to group bookings in gantt view
    office_id = fields.Many2one(related="room_id.office_id", string="Office", readonly=True, store=True)
    company_id = fields.Many2one(related="room_id.company_id", string="Company", readonly=True, store=True)

    @api.constrains("start_datetime", "stop_datetime")
    def _check_date_boundaries(self):
        for booking in self:
            if booking.start_datetime >= booking.stop_datetime:
                raise ValidationError(_(
                    "The start date of %(booking_name)s must be earlier than the end date.",
                    booking_name=booking.name
                ))

    @api.constrains("start_datetime", "stop_datetime")
    def _check_unique_slot(self):
        min_start = min(self.mapped("start_datetime"))
        max_stop = max(self.mapped("stop_datetime"))
        bookings_by_room = self.search([("room_id", "in", self.room_id.ids), ("start_datetime", "<", max_stop), ("stop_datetime", ">", min_start)]).grouped("room_id")
        for booking in self:
            if bookings_by_room.get(booking.room_id) and bookings_by_room[booking.room_id].filtered(
                lambda b: b.id != booking.id and b.start_datetime < booking.stop_datetime and b.stop_datetime > booking.start_datetime
            ):
                raise ValidationError(_(
                    "Room %(room_name)s is already booked during the selected time slot.",
                    room_name=booking.room_id.name
                ))

    # ------------------------------------------------------
    # CRUD / ORM
    # ------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        bookings = super(RoomBooking, self).create(vals_list)
        # Notify frontend views of new bookings
        for room, bookings in bookings.grouped("room_id").items():
            room._notify_booking_view("create", bookings)
        return bookings

    def unlink(self):
        # Notify frontend of deleted bookings
        bookings_by_room = self.grouped("room_id")
        for room, bookings in bookings_by_room.items():
            room._notify_booking_view("delete", bookings)
        return super(RoomBooking, self).unlink()

    def write(self, vals):
        bookings_by_room = self.grouped("room_id")
        res = super(RoomBooking, self).write(vals)
        # Notify frontend of updated bookings
        if new_room_id := vals.get("room_id"):
            new_room = self.env["room.room"].browse(new_room_id)
            for room, bookings in bookings_by_room.items():
                room._notify_booking_view("delete", bookings)
                new_room._notify_booking_view("create", bookings)
        elif {"name", "start_datetime", "stop_datetime"} & vals.keys():
            for room, bookings in bookings_by_room.items():
                room._notify_booking_view("update", bookings)
        return res

    @api.model
    def _read_group_room_id(self, rooms, domain):
        # Display all the rooms in the gantt view even if they have no booking,
        # and order them by office first, then by usual order (because the
        # office name is shown in the display name)
        if self.env.context.get("room_booking_gantt_show_all_rooms"):
            return rooms.search([], order=f"office_id, {rooms._order}")
        return rooms

    @api.model
    def get_empty_list_help(self, help_message):
        result_help_message = super().get_empty_list_help(help_message)
        if self.env.user.has_group('room.group_room_manager') and not self.env["room.room"].search_count([]):
            result_help_message += Markup('<a class="btn btn-outline-primary" href="/odoo/rooms/meeting-rooms/new">%s</a>') % _("Create a Room")
        return result_help_message
