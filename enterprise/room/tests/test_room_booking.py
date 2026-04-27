from datetime import datetime
from freezegun import freeze_time

from odoo.addons.room.tests.common import RoomCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestRoomBooking(RoomCommon):

    def test_next_booking_start(self):
        """
        Test that next_booking_start returns the start datetime of next meeting.
        """
        # Setup from RoomCommon:
        # Booking 1: 2023-05-15 10:00 -> 11:00
        # Booking 2: 2023-05-15 11:00 -> 12:00
        room = self.rooms[0]

        with freeze_time("2023-05-15 09:00:00"):
            room.invalidate_recordset(['next_booking_start'])
            self.assertEqual(
                room.next_booking_start,
                datetime(2023, 5, 15, 10, 0),
                "When room is free, next_booking_start should return the start time of the upcoming meeting."
            )

        with freeze_time("2023-05-15 10:30:00"):
            room.invalidate_recordset(['next_booking_start', 'is_available'])
            self.assertEqual(
                room.next_booking_start,
                datetime(2023, 5, 15, 11, 0),
                "When room is busy, next_booking_start should return the start time of the upcoming meeting"
            )
