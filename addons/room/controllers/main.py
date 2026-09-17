from werkzeug import exceptions

from odoo import fields, http
from odoo.http import request

BOOKING_FIELDS = {"name": "name", "start_datetime": "start", "stop_datetime": "stop"}


class RoomController(http.Controller):
    @http.route(
        "/room/<string:short_code>/book", type="http", auth="public", website=True
    )
    def room_book(self, short_code):
        room_sudo = self._get_room_sudo([("short_code", "=", short_code)])
        return request.render("room.room_booking", {"room": room_sudo})

    @http.route(
        "/room/<string:access_token>/get_existing_bookings",
        type="jsonrpc",
        auth="public",
    )
    def get_existing_bookings(self, access_token):
        room_sudo = self._get_room_from_access_token(access_token)
        now = fields.Datetime.now()
        bookings = [
            event._get_room_booking_values()
            for event in room_sudo._get_room_bookings([("stop", ">", now)])
        ]
        blocks = [
            {
                "id": -reservation.id,
                "name": request.env._("Unavailable"),
                "start_datetime": fields.Datetime.to_string(reservation.date_start),
                "stop_datetime": fields.Datetime.to_string(reservation.date_end),
                "readonly": True,
            }
            for reservation in room_sudo._get_room_blocks(now)
        ]
        return sorted(bookings + blocks, key=lambda booking: booking["start_datetime"])

    @http.route("/room/<string:access_token>/background", type="http", auth="public")
    def room_background_image(self, access_token):
        room_sudo = self._get_room_from_access_token(access_token)
        if not room_sudo.room_background_image:
            return ""
        return (
            request.env["ir.binary"]
            ._get_stream_image_from_record(room_sudo, "room_background_image")
            .prepare_response()
        )

    @http.route(
        "/room/<string:access_token>/booking/create", type="jsonrpc", auth="public"
    )
    def room_booking_create(self, access_token, name, start_datetime, stop_datetime):
        room_sudo = self._get_room_from_access_token(access_token)
        return (
            request.env["calendar.event"]
            ._create_room_booking(room_sudo, name, start_datetime, stop_datetime)
            .id
        )

    @http.route(
        "/room/<string:access_token>/booking/<int:booking_id>/delete",
        type="jsonrpc",
        auth="public",
    )
    def room_booking_delete(self, access_token, booking_id):
        return self._get_booking(booking_id, access_token).unlink()

    @http.route(
        "/room/<string:access_token>/booking/<int:booking_id>/update",
        type="jsonrpc",
        auth="public",
    )
    def room_booking_update(self, access_token, booking_id, **kwargs):
        return self._get_booking(booking_id, access_token).write(
            {
                fname: kwargs[key]
                for key, fname in BOOKING_FIELDS.items()
                if kwargs.get(key)
            }
        )

    def _get_booking(self, booking_id, access_token):
        room_sudo = self._get_room_from_access_token(access_token)
        booking_sudo = room_sudo._get_room_bookings([("id", "=", booking_id)])
        if not booking_sudo:
            raise exceptions.NotFound
        return booking_sudo.with_context(no_mail_to_attendees=True)

    def _get_room_from_access_token(self, access_token):
        return self._get_room_sudo([("access_token", "=", access_token)])

    def _get_room_sudo(self, domain):
        room_sudo = request.env["resource.resource"].sudo().search(domain, limit=1)
        if not room_sudo:
            raise exceptions.NotFound
        return room_sudo
