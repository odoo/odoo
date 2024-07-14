# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import TransactionCase

class RoomCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.office = cls.env["room.office"].create({
            "name": "Office 1",
        })
        cls.rooms = cls.env["room.room"].create([
            {
                "name": "Room 1",
                "office_id": cls.office.id,
                "short_code": "room_1",
            }, {
                "name": "Room 2",
                "office_id": cls.office.id,
            },
        ])
        cls.bookings = cls.env["room.booking"].create([
            {
                "name": "Booking 1",
                "room_id": cls.rooms[0].id,
                "start_datetime": datetime(2023, 5, 15, 10, 0),
                "stop_datetime": datetime(2023, 5, 15, 11, 0),
            }, {
                "name": "Booking 2",
                "room_id": cls.rooms[0].id,
                "start_datetime": datetime(2023, 5, 15, 11, 0),
                "stop_datetime": datetime(2023, 5, 15, 12, 0),
            }
        ])
