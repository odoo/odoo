from datetime import datetime

from odoo import exceptions
from odoo.tests.common import tagged, users

from odoo.addons.mail.tests.common import MailCase, mail_new_test_user
from odoo.addons.room.tests.common import RoomCommon


@tagged("room_acl", "post_install", "-at_install")
class TestRoomSecurity(RoomCommon, MailCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee = mail_new_test_user(
            cls.env,
            groups="base.group_user,base.group_partner_manager",
            login="employee",
            name="Ernest Employee",
            notification_type="inbox",
        )
        cls.room_manager = mail_new_test_user(
            cls.env,
            groups="room.group_room_manager",
            login="room_manager",
            name="Room Manager",
        )
        cls.public_user = mail_new_test_user(
            cls.env,
            groups="base.group_public",
            login="public_user",
            name="Public user",
        )
        cls.vehicle = cls.env["resource.asset"].create(
            {
                "name": "Van",
                "kind_id": cls.env.ref("resource_asset.kind_vehicle").id,
            }
        )
        cls.bookings[0].user_id = cls.user_employee

    @users("public_user")
    def test_models_as_public(self):
        with self.assertRaises(exceptions.AccessError):
            self.env["calendar.event"].search([])
        with self.assertRaises(exceptions.AccessError):
            self.env["resource.asset"].search([])

    @users("employee")
    def test_an_employee_books_rooms_for_their_own_meetings(self):
        with self.assertRaises(exceptions.AccessError):
            self.rooms[0].with_env(self.env).write({"name": "Room 2"})

        own = self.bookings[0].with_env(self.env)
        own.write(
            {
                "name": "rescheduled",
                "resource_ids": self.resources[1].ids,
                "start": datetime(2023, 5, 15, 7, 0),
                "stop": datetime(2023, 5, 15, 8, 0),
            }
        )
        self.assertEqual(own.reservation_ids.resource_id, self.rooms[1].resource_id)
        new = (
            self.env["calendar.event"]
            .with_env(self.env)
            .create(
                {
                    **self._booking_vals("morning meeting", self.resources[0], 13, 14),
                    "user_id": self.env.user.id,
                }
            )
        )
        self.assertEqual(new.resource_ids, self.resources[0])
        new.unlink()

        with self.assertRaises(exceptions.AccessError):
            self.bookings[1].with_env(self.env).write(
                {"resource_ids": self.resources[1].ids}
            )

    @users("room_manager")
    def test_a_room_manager_manages_rooms_and_not_other_assets(self):
        self.rooms[0].with_env(self.env).write({"name": "Room 2"})
        new_room = (
            self.env["resource.asset.room"]
            .with_env(self.env)
            .create(
                {
                    "name": "New Room",
                    "kind_id": self.env.ref("room.kind_room").id,
                    "state": "in_service",
                    "address_id": self.office.id,
                }
            )
        )
        self.assertTrue(new_room.resource_id.access_token)
        new_room.room_short_code = "new_room"

        with self.assertRaises(exceptions.AccessError):
            self.vehicle.with_env(self.env).write({"name": "Truck"})

        self.bookings[1].with_env(self.env).write(
            {
                "start": datetime(2023, 5, 15, 16, 0),
                "stop": datetime(2023, 5, 15, 17, 0),
            }
        )

    @users("room_manager")
    def test_a_room_manager_writes_the_resource_of_a_room_and_not_of_a_vehicle(self):
        self.rooms[0].with_env(self.env).resource_id.write({"name": "Room 2"})
        with self.assertRaises(exceptions.AccessError):
            self.vehicle.with_env(self.env).resource_id.write({"name": "Truck"})
