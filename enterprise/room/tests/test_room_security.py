# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import exceptions
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.room.tests.common import RoomCommon
from odoo.tests.common import tagged, users

@tagged("room_acl")
class TestRoomSecurity(RoomCommon, MailCommon):
    """Test ACLs on models"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.room_manager = mail_new_test_user(
            cls.env,
            groups='room.group_room_manager',
            login='room_manager',
            name='Room Manager',
        )

        cls.public_user = mail_new_test_user(
            cls.env,
            groups='base.group_public',
            login='public_user',
            name='Public user',
        )

    @users('public_user')
    def test_models_as_public(self):
        # Booking
        with self.assertRaises(exceptions.AccessError, msg="ACLs: No Booking access to public"):
            self.env["room.booking"].search([])

        # Office
        with self.assertRaises(exceptions.AccessError, msg="ACLs: No Office access to public"):
            self.env["room.office"].search([])

        # Room
        with self.assertRaises(exceptions.AccessError, msg="ACLs: No Room access to public"):
            self.env["room.room"].search([])

    @users('employee')
    def test_models_as_employee(self):
        # Office
        with self.assertRaises(exceptions.AccessError, msg="ACLs: Readonly access on office"):
            self.office.with_env(self.env).write({"name": "Office 2"})

        # Room
        with self.assertRaises(exceptions.AccessError, msg="ACLs: Readonly access on room"):
            self.rooms[0].with_env(self.env).write({"name": "Room 2"})

        # Booking
        self.bookings[0].with_env(self.env).write({
            "name": "rescheduled",
            "room_id": self.rooms[1].id,
            "start_datetime": datetime(2023, 5, 15, 7, 0),
            "stop_datetime": datetime(2023, 5, 15, 8, 0),
        })
        self.env["room.booking"].with_env(self.env).create({
            "name": "morning meeting",
            "room_id": self.rooms[0].id,
            "start_datetime": datetime(2023, 5, 15, 10, 0),
            "stop_datetime": datetime(2023, 5, 15, 11, 0),
        })
        self.bookings[1].with_env(self.env).unlink()

    @users('room_manager')
    def test_models_as_manager(self):
        # Office
        self.office.with_env(self.env).write({"name": "Office 2"})
        new_office = self.env["room.office"].with_env(self.env).create({"name": "New Office"})
        new_office.unlink()

        # Room
        self.rooms[0].with_env(self.env).write({"name": "Room 2"})
        new_room = self.env["room.room"].with_env(self.env).create({
            "name": "New Room",
            "office_id": self.office.id,
        })
        new_room.unlink()

        # Booking
        self.bookings[0].with_env(self.env).write({
            "name": "rescheduled",
            "room_id": self.rooms[1].id,
            "start_datetime": datetime(2023, 5, 15, 7, 0),
            "stop_datetime": datetime(2023, 5, 15, 8, 0),
        })
        self.env["room.booking"].with_env(self.env).create({
            "name": "morning meeting",
            "room_id": self.rooms[0].id,
            "start_datetime": datetime(2023, 5, 15, 10, 0),
            "stop_datetime": datetime(2023, 5, 15, 11, 0),
        })
        self.bookings[1].with_env(self.env).unlink()
