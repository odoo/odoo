from datetime import datetime

from freezegun import freeze_time

from odoo.tests.common import HttpCase, JsonRpcException, tagged

from odoo.addons.room.tests.common import RoomCommon


@tagged("post_install", "-at_install")
class TestRoomFrontend(RoomCommon, HttpCase):
    @freeze_time("2023-05-15 11:15:00")
    def test_room_frontend(self):
        self.authenticate(None, None)
        res = self.url_open(f"/room/{self.resources[0].short_code}/book")
        self.assertEqual(res.status_code, 200)

        access_token = self.resources[0].access_token
        booking_id = self.call_jsonrpc(
            f"/room/{access_token}/booking/create",
            {
                "name": "public booking",
                "start_datetime": "2023-05-15 14:00:00",
                "stop_datetime": "2023-05-15 15:00:00",
            },
        )
        booking = self.env["calendar.event"].browse(booking_id)
        self.assertEqual(booking.name, "public booking")
        self.assertEqual(booking.resource_ids, self.resources[0])
        self.assertFalse(booking.user_id)
        self.assertEqual(booking.reservation_ids.enforcement_mode, "soft")
        self.assertTrue(booking.reservation_ids.resource_id.enforce_booking_limit)

        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self.call_jsonrpc(
                f"/room/{access_token[1:]}/booking/create",
                {
                    "name": "public booking",
                    "start_datetime": "2023-05-15 15:00:00",
                    "stop_datetime": "2023-05-15 16:00:00",
                },
            )

        self.env["resource.reservation"].create(
            {
                "name": "Repainting",
                "resource_id": self.rooms[0].resource_id.id,
                "date_start": datetime(2023, 5, 15, 16, 0),
                "date_end": datetime(2023, 5, 15, 17, 0),
                "enforcement_mode": "hard",
            }
        )
        bookings = self.call_jsonrpc(f"/room/{access_token}/get_existing_bookings", {})
        self.assertEqual(
            [(b["start_datetime"], b.get("readonly", False)) for b in bookings],
            [
                ("2023-05-15 11:00:00", False),
                ("2023-05-15 14:00:00", False),
                ("2023-05-15 16:00:00", True),
            ],
        )

        self.call_jsonrpc(
            f"/room/{access_token}/booking/{self.bookings[1].id}/update",
            {
                "name": "rescheduled booking",
                "start_datetime": "2023-05-15 12:00:00",
                "stop_datetime": "2023-05-15 13:00:00",
            },
        )
        self.assertEqual(self.bookings[1].name, "rescheduled booking")
        self.assertEqual(self.bookings[1].start, datetime(2023, 5, 15, 12, 0))
        self.assertEqual(self.bookings[1].stop, datetime(2023, 5, 15, 13, 0))

        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self.call_jsonrpc(
                f"/room/{self.resources[1].access_token}/booking/{self.bookings[1].id}/update",
                {
                    "name": "failed reschedule",
                    "start_datetime": "2023-05-15 13:00:00",
                    "stop_datetime": "2023-05-15 14:00:00",
                },
            )
        self.assertEqual(self.bookings[1].name, "rescheduled booking")

        self.call_jsonrpc(
            f"/room/{access_token}/booking/{self.bookings[1].id}/delete", {}
        )
        self.assertFalse(self.bookings[1].exists())

        with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
            self.call_jsonrpc(
                f"/room/{self.resources[1].access_token}/booking/{self.bookings[0].id}/delete",
                {},
            )
        self.assertTrue(self.bookings[0].exists())

    def test_room_backend_tour(self):
        self.start_tour("/odoo/meeting-rooms", "room_backend_tour", login="admin")
        booking = self.env["calendar.event"].search([("name", "=", "Tour meeting")])
        self.assertEqual(booking.resource_ids, self.resources[1])
        self.assertEqual(booking.reservation_ids.resource_id, self.rooms[1].resource_id)
        self.assertEqual(booking.appointment_type_id, self.room_type)
