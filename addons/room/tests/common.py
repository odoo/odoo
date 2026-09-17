from datetime import datetime

from odoo import Command
from odoo.tests.common import TransactionCase


class RoomCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, no_mail_to_attendees=True))
        cls.office = cls.env["res.partner"].create(
            {"name": "Office 1", "type": "other"}
        )
        cls.rooms = cls.env["resource.asset"].create(
            [
                {
                    "name": "Room 1",
                    "kind_id": cls.env.ref("room.kind_room").id,
                    "state": "in_service",
                    "address_id": cls.office.id,
                },
                {
                    "name": "Room 2",
                    "kind_id": cls.env.ref("room.kind_room").id,
                    "state": "in_service",
                    "address_id": cls.office.id,
                },
            ]
        )
        cls.resources = cls.rooms.resource_id
        cls.resources[0].short_code = "room_1"
        cls.room_type = cls.env.ref("room.appointment_type_room")
        cls.bookings = cls.env["calendar.event"].create(
            [
                cls._booking_vals("Booking 1", cls.resources[0], 10, 11),
                cls._booking_vals("Booking 2", cls.resources[0], 11, 12),
            ]
        )

    @classmethod
    def _booking_vals(cls, name, resource, start_hour, stop_hour, day=15):
        return {
            "name": name,
            "start": datetime(2023, 5, day, start_hour, 0),
            "stop": datetime(2023, 5, day, stop_hour, 0),
            "appointment_type_id": cls.room_type.id,
            "booking_line_ids": [
                Command.create(
                    {"resource_id": resource.id, "capacity_reserved": 1}
                )
            ],
        }
