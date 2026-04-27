# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.addons.room.tests.common import RoomCommon
from odoo.tests.common import HttpCase, JsonRpcException, tagged

@tagged("post_install", "-at_install")
class TestRoomFrontend(RoomCommon, HttpCase):

    @freeze_time("2023-05-15 11:15:00")
    def test_room_frontend(self):
        self.authenticate(None, None)
        res = self.url_open(f"/room/{self.rooms[0].short_code}/book")
        self.assertEqual(res.status_code, 200)

        access_token = self.rooms[0].access_token
        # Create a booking
        res = self.make_jsonrpc_request(f"/room/{access_token}/booking/create", {
            "name": "public booking",
            "start_datetime": "2023-05-15 14:00:00",
            "stop_datetime": "2023-05-15 15:00:00",
        })
        self.assertTrue(self.env["room.booking"].search([
            ("name", "=", "public booking"),
            ("room_id", "=", self.rooms[0].id)
        ]))
        # Create with invalid access token
        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self.make_jsonrpc_request(f"/room/{access_token[1:]}/booking/create", {
                "name": "public booking",
                "start_datetime": "2023-05-15 15:00:00",
                "stop_datetime": "2023-05-15 16:00:00",
            })

        # Get existing bookings (should not fetch ended booking)
        bookings = self.make_jsonrpc_request(f"/room/{access_token}/get_existing_bookings", {})
        self.assertEqual(len(bookings), 2)
        self.assertEqual(bookings[0]["start_datetime"], "2023-05-15 11:00:00")

        # Reschedule the current booking
        self.make_jsonrpc_request(f"/room/{access_token}/booking/{self.bookings[1].id}/update", {
            "name": "rescheduled booking",
            "start_datetime": "2023-05-15 12:00:00",
            "stop_datetime": "2023-05-15 13:00:00",
        })
        self.assertEqual(self.bookings[1].name, "rescheduled booking")
        self.assertEqual(self.bookings[1].start_datetime, datetime(2023, 5, 15, 12, 0))
        self.assertEqual(self.bookings[1].stop_datetime, datetime(2023, 5, 15, 13, 0))

        # Update a booking with the access token of another room
        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self.make_jsonrpc_request(f"/room/{self.rooms[1].access_token}/booking/{self.bookings[1].id}/update", {
                "name": "failed reschedule",
                "start_datetime": "2023-05-15 13:00:00",
                "stop_datetime": "2023-05-15 14:00:00",
            })
        self.assertEqual(self.bookings[1].name, "rescheduled booking")

        # Delete a booking
        self.make_jsonrpc_request(f"/room/{access_token}/booking/{self.bookings[1].id}/delete", {})
        self.assertEqual(self.env["room.booking"].search_count([("room_id", "=", self.rooms[0].id)]), 2)

        # Delete a booking with the access token of another room
        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self.make_jsonrpc_request(f"/room/{self.rooms[1].access_token}/booking/{self.bookings[0].id}/delete", {})
        self.assertEqual(self.env["room.booking"].search_count([("room_id", "=", self.rooms[0].id)]), 2)
