from datetime import datetime
from unittest.mock import patch

from freezegun import freeze_time
from psycopg import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.room.tests.common import RoomCommon


@tagged("post_install", "-at_install")
class TestRoomBooking(RoomCommon):
    def test_a_room_is_a_bookable_asset_with_a_kiosk(self):
        room = self.rooms[0]
        self.assertIn(self.room_type, room.resource_id.appointment_type_ids)
        self.assertTrue(room.resource_id.access_token)
        self.assertTrue(self.resources[1].short_code)
        self.assertTrue(room.resource_id.enforce_booking_limit)
        self.assertEqual(room.display_name, "Office 1 - Room 1")

    def test_an_asset_that_becomes_a_room_gets_its_kiosk(self):
        asset = self.env["resource.asset"].create(
            {
                "name": "Board room",
                "kind_id": self.env.ref("resource_asset.kind_property").id,
                "state": "in_service",
            }
        )
        self.assertFalse(asset.resource_id.access_token)
        asset.kind_id = self.env.ref("room.kind_room")
        self.assertTrue(asset.resource_id.access_token)

    def test_a_booking_holds_the_whole_room(self):
        reservation = self.bookings[0].reservation_ids
        self.assertEqual(reservation.resource_id, self.rooms[0].resource_id)
        self.assertEqual(reservation.allocated_percentage, 100.0)

    def test_overlapping_bookings_are_refused(self):
        with self.assertRaises(ValidationError):
            self.env["calendar.event"].create(
                self._booking_vals("Meeting", self.resources[0], 10, 11)
            )
        with self.assertRaises(ValidationError):
            self.env["calendar.event"].create(
                [
                    self._booking_vals("Meeting 1", self.resources[0], 13, 15),
                    self._booking_vals("Meeting 2", self.resources[0], 14, 16),
                ]
            )
        self.env["calendar.event"].create(
            self._booking_vals("Other room", self.resources[1], 10, 11)
        )

    def test_a_reservation_from_elsewhere_blocks_the_room(self):
        self.env["resource.reservation"].create(
            {
                "name": "Repainting",
                "resource_id": self.rooms[0].resource_id.id,
                "date_start": datetime(2023, 5, 16, 8, 0),
                "date_end": datetime(2023, 5, 16, 18, 0),
                "enforcement_mode": "hard",
                "res_model": "maintenance.order",
                "res_id": 1,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["calendar.event"].create(
                self._booking_vals("Meeting", self.resources[0], 9, 10, day=16)
            )
        blocks = self.resources[0]._get_room_blocks(datetime(2023, 5, 16, 0, 0))
        self.assertEqual(blocks.mapped("name"), ["Repainting"])

    def test_a_room_out_of_service_refuses_bookings(self):
        self.rooms[1].action_set_out_of_service()
        with self.assertRaises(ValidationError):
            self.env["calendar.event"].create(
                self._booking_vals("Meeting", self.resources[1], 9, 10)
            )

    def test_next_booking_start_and_availability_read_the_ledger(self):
        room = self.resources[0]
        with freeze_time("2023-05-15 09:00:00"):
            room.invalidate_recordset(["next_booking_start", "is_available"])
            self.assertTrue(room.is_available)
            self.assertEqual(room.next_booking_start, datetime(2023, 5, 15, 10, 0))
        with freeze_time("2023-05-15 10:30:00"):
            room.invalidate_recordset(["next_booking_start", "is_available"])
            self.assertFalse(room.is_available)
            self.assertEqual(room.next_booking_start, datetime(2023, 5, 15, 11, 0))
            self.assertFalse(self.rooms[0].room_is_available)

    def test_a_booking_moved_to_another_room_leaves_the_first_kiosk(self):
        sent = []
        with patch.object(
            type(self.env["bus.bus"]),
            "_sendone",
            autospec=True,
            side_effect=lambda _bus, channel, notification, payload: sent.append(
                notification
            ),
        ):
            self.bookings[0].write(
                {"name": "moved", "resource_ids": self.resources[1].ids}
            )
        left = f"room#{self.resources[0].id}/booking/"
        self.assertNotIn(
            f"{left}update", sent, "the room the booking left must not keep showing it"
        )
        self.assertIn(f"{left}delete", sent)
        self.assertIn(f"room#{self.resources[1].id}/booking/create", sent)

    def test_an_asset_already_offered_gets_its_kiosk_when_it_becomes_a_room(self):
        asset = self.env["resource.asset"].create(
            {
                "name": "Projector",
                "kind_id": self.env.ref("resource_asset.kind_equipment").id,
                "state": "in_service",
            }
        )
        offer = self.env["appointment.type"].create(
            {"name": "Equipment booking", "schedule_based_on": "resources"}
        )
        asset.resource_id.appointment_type_ids = offer
        self.assertFalse(asset.resource_id.access_token)
        asset.kind_id = self.env.ref("room.kind_room")
        self.assertTrue(asset.resource_id.access_token)
        self.assertTrue(asset.resource_id.short_code)
        self.assertIn(self.room_type, asset.resource_id.appointment_type_ids)
        self.assertIn(offer, asset.resource_id.appointment_type_ids)
        self.assertTrue(asset.resource_id.enforce_booking_limit)

    @mute_logger("odoo.db.cursor")
    def test_kiosk_codes_are_unique(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.resources[1].short_code = self.resources[0].short_code
            self.resources[1].flush_recordset()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.resources[1].access_token = self.resources[0].access_token
            self.resources[1].flush_recordset()
