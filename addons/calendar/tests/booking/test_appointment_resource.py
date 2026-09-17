from datetime import UTC, datetime, timedelta

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged, users, warmup

from odoo.addons.calendar.tests.booking.common import AppointmentCommon


@tagged("appointment_resources", "post_install", "-at_install")
class AppointmentResource(AppointmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.appointment_manage_capacity, cls.appointment_regular = cls.env[
            "appointment.type"
        ].create(
            [
                {
                    "appointment_tz": "UTC",
                    "min_schedule_hours": 1.0,
                    "max_schedule_days": 8,
                    "name": "Managed Test",
                    "manage_capacity": True,
                    "schedule_based_on": "resources",
                    "slot_ids": [
                        (
                            0,
                            0,
                            {
                                "weekday": str(cls.reference_monday.isoweekday()),
                                "start_hour": 6,
                                "end_hour": 18,
                            },
                        )
                    ],
                },
                {
                    "appointment_tz": "UTC",
                    "min_schedule_hours": 1.0,
                    "max_schedule_days": 8,
                    "name": "Unmanaged Test",
                    "manage_capacity": False,
                    "schedule_based_on": "resources",
                    "slot_ids": [
                        (
                            0,
                            0,
                            {
                                "weekday": str(cls.reference_monday.isoweekday()),
                                "start_hour": 6,
                                "end_hour": 18,
                            },
                        )
                    ],
                },
            ]
        )

        cls.resource_1, cls.resource_2, cls.resource_3 = cls.env[
            "resource.resource"
        ].create(
            [
                {
                    "appointment_type_ids": cls.appointment_manage_capacity.ids,
                    "capacity": 3,
                    "name": "Resource 1",
                },
                {
                    "appointment_type_ids": cls.appointment_manage_capacity.ids,
                    "capacity": 2,
                    "name": "Resource 2",
                    "booking_exclusive": False,
                },
                {
                    "appointment_type_ids": (
                        cls.appointment_manage_capacity | cls.appointment_regular
                    ).ids,
                    "capacity": 1,
                    "name": "Resource 3",
                },
            ]
        )

    @users("apt_manager")
    def test_appointment_resource_default_appointment_type(self):
        """Check that the default appointment type is properly deduced from the default appointment resource."""
        resource_3_type_ids = self.resource_3.appointment_type_ids
        Event = self.env["calendar.event"]

        states = [
            (self.resource_3, None, resource_3_type_ids[0]),
            (self.resource_3, resource_3_type_ids[1], resource_3_type_ids[1]),
        ]
        for resource, default_type, expected_type_id in states:
            context = {
                "booking_gantt_create_record": True,
                "default_resource_ids": resource.ids,
            }
            if default_type:
                context.update(default_appointment_type_id=default_type.id)

            event = Form(Event.with_context(context))
            self.assertEqual(event.appointment_type_id, expected_type_id)

    @users("apt_manager")
    def test_appointment_resource_link(self):
        """Test link between resources when they are combinable."""
        resource_1, resource_2 = self.env["resource.resource"].create(
            [
                {
                    "capacity": 4,
                    "name": "Table of 4",
                },
                {
                    "capacity": 2,
                    "name": "Table of 2",
                },
            ]
        )
        self.assertFalse(resource_1.combinable_resource_ids)
        self.assertFalse(resource_2.combinable_resource_ids)

        # Test: link resource 2 to resource 1, and add a new resource as an
        # embedded 2many creation
        resource_1.write(
            {
                "combinable_resource_ids": [
                    (4, resource_2.id),  # new link
                    (
                        0,
                        0,
                        {  # embedded creation
                            "capacity": 1,
                            "name": "OnTheFly Table of 1",
                        },
                    ),
                ],
            }
        )
        new_resource_1 = self.env["resource.resource"].search(
            [("name", "=", "OnTheFly Table of 1")]
        )
        self.assertEqual(len(new_resource_1), 1, "Should have created a new resource")
        self.assertEqual(
            new_resource_1.combinable_resource_ids, resource_1, "Link works both ways"
        )
        self.assertFalse(new_resource_1.source_resource_ids)
        self.assertEqual(
            new_resource_1.destination_resource_ids,
            resource_1,
            "Resource 2 is destination of link between 1 and 2",
        )
        self.assertEqual(
            resource_1.combinable_resource_ids,
            resource_2 + new_resource_1,
            "Resource 1 should be linked to linked resource 2 and newly created new",
        )
        self.assertEqual(resource_1.source_resource_ids, resource_2 + new_resource_1)
        self.assertFalse(resource_1.destination_resource_ids)
        self.assertEqual(
            resource_2.combinable_resource_ids, resource_1, "Link works both ways"
        )
        self.assertFalse(resource_2.source_resource_ids)
        self.assertEqual(
            resource_2.destination_resource_ids,
            resource_1,
            "Resource 2 is destination of link between 1 and 2",
        )

        # Test: break link to resource 2, add an existing one (check duplication)
        # and create yet another one
        resource_1.write(
            {
                "combinable_resource_ids": [
                    (3, resource_2.id),  # break link
                    (4, new_resource_1.id),  # already existing
                    (0, 0, {"capacity": 1, "name": "OnTheFly Table of 1 (bis)"}),
                ],
            }
        )
        new_resource_2 = self.env["resource.resource"].search(
            [("name", "=", "OnTheFly Table of 1 (bis)")]
        )
        self.assertEqual(len(new_resource_2), 1, "Should have created a new resource")
        self.assertEqual(
            new_resource_1.combinable_resource_ids, resource_1, "Link works both ways"
        )
        self.assertFalse(new_resource_1.source_resource_ids)
        self.assertEqual(new_resource_1.destination_resource_ids, resource_1)
        self.assertEqual(
            new_resource_2.combinable_resource_ids, resource_1, "Link works both ways"
        )
        self.assertFalse(new_resource_2.source_resource_ids)
        self.assertEqual(new_resource_2.destination_resource_ids, resource_1)
        self.assertEqual(
            resource_1.combinable_resource_ids,
            new_resource_1 + new_resource_2,
            "Resource 1 should be linked to linked resource 2 and newly created new",
        )
        self.assertEqual(
            resource_1.source_resource_ids, new_resource_1 + new_resource_2
        )
        self.assertFalse(resource_1.destination_resource_ids)
        self.assertFalse(resource_2.combinable_resource_ids)
        self.assertFalse(resource_2.source_resource_ids)
        self.assertFalse(resource_2.destination_resource_ids)

        # Test: update link based on destination, not source as previous tests
        resource_2.write(
            {
                "combinable_resource_ids": [
                    (4, new_resource_1.id),  # add a new entry in destination
                ]
            }
        )
        new_resource_2.write(
            {
                "combinable_resource_ids": [
                    (3, resource_1.id),  # break link
                    (4, resource_2.id),  # new link, will have both sources and dest
                    (4, new_resource_1.id),  # new link
                ]
            }
        )
        self.assertEqual(len(new_resource_2), 1, "Should have created a new resource")
        self.assertEqual(
            new_resource_1.combinable_resource_ids,
            resource_1 + resource_2 + new_resource_2,
        )
        self.assertFalse(new_resource_1.source_resource_ids)
        self.assertEqual(
            new_resource_1.destination_resource_ids,
            resource_1 + resource_2 + new_resource_2,
        )
        self.assertEqual(
            new_resource_2.combinable_resource_ids, resource_2 + new_resource_1
        )
        self.assertEqual(
            new_resource_2.source_resource_ids, resource_2 + new_resource_1
        )
        self.assertFalse(new_resource_2.destination_resource_ids)
        self.assertEqual(resource_1.combinable_resource_ids, new_resource_1)
        self.assertEqual(resource_1.source_resource_ids, new_resource_1)
        self.assertFalse(resource_1.destination_resource_ids)
        self.assertEqual(
            resource_2.combinable_resource_ids, new_resource_1 + new_resource_2
        )
        self.assertEqual(resource_2.source_resource_ids, new_resource_1)
        self.assertEqual(resource_2.destination_resource_ids, new_resource_2)

    @users("apt_manager")
    def test_appointment_resource_not_taking_responsible_capacity(self):
        """Test that resource booking lines do not reserve any capacity of the responsible user"""
        resource_appointment = self.appointment_manage_capacity
        user_appointment = self.env["appointment.type"].create(
            [
                {
                    "appointment_tz": "UTC",
                    "manage_capacity": False,
                    "max_bookings": 2,
                    "max_schedule_days": 5,
                    "min_schedule_hours": 1.0,
                    "name": "User Appointment",
                    "schedule_based_on": "users",
                    "slot_ids": [
                        (
                            0,
                            0,
                            {
                                "weekday": str(self.reference_monday.isoweekday()),
                                "start_hour": 14,
                                "end_hour": 15,
                            },
                        )
                    ],
                    "staff_user_ids": self.staff_user_bxls.ids,
                }
            ]
        )
        staff_user = self.staff_user_bxls
        self.assertEqual(len(user_appointment.staff_user_ids), 1)

        start = datetime(2022, 2, 14, 14, 0, 0)
        end = start + timedelta(hours=1)

        # Create conflicting events. Remaining capacity should be 1, as resource booking should not count.
        self.env["calendar.event"].with_context(self._test_context).create(
            [
                {
                    "appointment_type_id": user_appointment.id,
                    "attendee_ids": [
                        (
                            0,
                            0,
                            {
                                "partner_id": staff_user.partner_id.id,
                                "state": "accepted",
                            },
                        )
                    ],
                    "booking_line_ids": [
                        (
                            0,
                            0,
                            {
                                "appointment_user_id": staff_user.id,
                                "capacity_reserved": 1,
                                "capacity_used": 1,
                            },
                        )
                    ],
                    "name": "Booking User",
                    "partner_ids": [(4, staff_user.partner_id.id)],
                    "start": start,
                    "stop": end,
                    "user_id": staff_user.id,
                },
                {
                    "appointment_type_id": resource_appointment.id,
                    "booking_line_ids": [
                        (
                            0,
                            0,
                            {
                                "resource_id": self.resource_1.id,
                                "capacity_reserved": 1,
                                "capacity_used": self.resource_1.capacity,
                            },
                        )
                    ],
                    "name": "Booking Resource",
                    "start": start,
                    "stop": end,
                    "user_id": staff_user.id,
                },
            ]
        )

        with freeze_time(self.reference_now):
            slots = user_appointment._get_appointment_slots("UTC", asked_capacity=1)
            user_slots = self._filter_appointment_slots(slots)

        self.assertEqual(len(user_slots), 1)
        self.assertTrue(user_slots[0]["staff_user_id"], staff_user.id)
        self.assertEqual(
            user_appointment._get_users_remaining_capacity(staff_user, start, end)[
                "total_remaining_capacity"
            ],
            1,
        )

    @users("apt_manager")
    def test_appointment_resources_remaining_capacity(self):
        """Test that the remaining capacity of resources are correctly computed"""
        appointment = self.appointment_manage_capacity
        resource_1 = self.resource_1
        resource_2 = self.resource_2

        start = datetime(2022, 2, 15, 14, 0, 0)
        end = start + timedelta(hours=1)

        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_1, start, end)[
                "total_remaining_capacity"
            ]
            == 3
        )
        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_2, start, end)[
                "total_remaining_capacity"
            ]
            == 2
        )

        # Create bookings for resource
        booking_1, booking_2 = (
            self.env["calendar.event"]
            .with_context(self._test_context)
            .create(
                [
                    {
                        "appointment_type_id": appointment.id,
                        "booking_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "resource_id": resource_1.id,
                                    "capacity_reserved": 1,
                                    "capacity_used": resource_1.capacity,
                                },
                            )
                        ],
                        "name": "Booking 1",
                        "start": start,
                        "stop": end,
                    },
                    {
                        "appointment_type_id": appointment.id,
                        "booking_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "resource_id": resource_2.id,
                                    "capacity_reserved": 1,
                                },
                            )
                        ],
                        "name": "Booking 2",
                        "start": start,
                        "stop": end,
                    },
                ]
            )
        )
        bookings = booking_1 + booking_2

        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_1, start, end)[
                "total_remaining_capacity"
            ]
            == 0,
            "The resource should have no availabilities left",
        )
        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_2, start, end)[
                "total_remaining_capacity"
            ]
            == 1,
            "The resource should have 1 availability left because it is shareable",
        )

        bookings.unlink()
        resource_1.combinable_resource_ids = resource_2
        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_1, start, end)[
                "total_remaining_capacity"
            ]
            == 5,
            "The resource should have 5 availabilities (3 from the resource and 2 from the other linked to it)",
        )
        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_2, start, end)[
                "total_remaining_capacity"
            ]
            == 5
        )
        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_1, start, end)[
                resource_1
            ]
            == 3
        )
        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_2, start, end)[
                resource_2
            ]
            == 2
        )

        booking = (
            self.env["calendar.event"]
            .with_context(self._test_context)
            .create(
                [
                    {
                        "appointment_type_id": appointment.id,
                        "booking_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "resource_id": resource_1.id,
                                    "capacity_reserved": 3,
                                    "capacity_used": 3,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "resource_id": resource_2.id,
                                    "capacity_reserved": 1,
                                },
                            ),
                        ],
                        "name": "Booking",
                        "start": start,
                        "stop": end,
                    }
                ]
            )
        )

        self.assertTrue(len(booking.resource_ids) == 2)
        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_1, start, end)[
                "total_remaining_capacity"
            ]
            == 1,
            "The resource should have 1 availability left (the one from resource_2)",
        )
        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_1, start, end)[
                resource_1
            ]
            == 0,
            "The resource should have no availability left if alone",
        )
        self.assertTrue(
            appointment._get_resources_remaining_capacity(resource_2, start, end)[
                "total_remaining_capacity"
            ]
            == 1,
            "The resource should have 1 availability left",
        )

        self.assertDictEqual(
            appointment._get_resources_remaining_capacity(
                self.env["resource.resource"], start, end
            ),
            {"total_remaining_capacity": 0},
            "No result should give dict with correct accumulated values.",
        )

    @users("apt_user")
    def test_appointment_user_can_create_booking_with_resources_from_gantt(self):
        """Test if a user (with user rights) can create a booking from the calendar gantt view."""

        gantt_context = {
            "booking_gantt_create_record": True,
            "default_appointment_type_id": self.appointment_manage_capacity.id,
            "default_resource_ids": [self.resource_1.id],
        }

        booking_form = Form(self.env["calendar.event"].with_context(gantt_context))
        booking_form.name = "Gommage"
        booking = booking_form.save()

        self.assertEqual(booking.name, "Gommage")
        self.assertEqual(booking.appointment_type_id, self.appointment_manage_capacity)
        self.assertEqual(len(booking.resource_ids), 1)
        self.assertEqual(booking.resource_ids, self.resource_1)


@tagged("appointment_resources", "post_install", "-at_install")
class AppointmentResourceBookingTest(AppointmentCommon):
    @users("apt_manager")
    @warmup
    def test_appointment_resources(self):
        """Slots generation and availability of appointment type with resources"""
        appointment = self.env["appointment.type"].create(
            {
                "appointment_tz": "UTC",
                "is_auto_assign": True,
                "min_schedule_hours": 1.0,
                "max_schedule_days": 8,
                "name": "Test",
                "manage_capacity": True,
                "schedule_based_on": "resources",
                "slot_ids": [
                    (
                        0,
                        0,
                        {
                            "weekday": str(self.reference_monday.isoweekday()),
                            "start_hour": 6,
                            "end_hour": 18,
                        },
                    )
                ],
            }
        )

        self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": appointment.ids,
                    "capacity": 3,
                    "name": "Resource %s" % i,
                }
                for i in range(20)
            ]
        )
        # Flush everything, notably tracking values, as it may impact performances
        self.flush_tracking()

        with freeze_time(self.reference_now):
            with self.assertQueryCount(default=7):
                appointment._get_appointment_slots("UTC")

    def test_appointment_resources_check_organizer_validation_conditions(self):
        appointment_vals_list = [
            {
                "appointment_type_id": self.apt_type_resource.id,
                "name": "Booking",
                "start": datetime(2022, 2, 15, 14, 0, 0),
                "stop": datetime(2022, 2, 15, 15, 0, 0),
            },
            {
                "appointment_type_id": self.apt_type_bxls_2days.id,
                "name": "Booking",
                "start": datetime(2022, 2, 15, 10, 0, 0),
                "stop": datetime(2022, 2, 15, 11, 0, 0),
            },
            {
                "appointment_type_id": False,
                "name": "Booking",
                "start": datetime(2022, 2, 15, 10, 0, 0),
                "stop": datetime(2022, 2, 15, 11, 0, 0),
            },
        ]

        self.assertEqual(
            self.env["calendar.event"]._get_organizer_validation_conditions(
                appointment_vals_list
            ),
            [False, True, True],
        )

    @users("apt_manager")
    def test_appointment_resources_combinable(self):
        """Check that combinable resources are correctly process."""
        table_c2, table_c4, table_c6 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": i,
                    "name": "Table for %s" % i,
                    "booking_sequence": i,
                }
                for i in range(2, 7, 2)
            ]
        )

        table_c2.combinable_resource_ids = table_c4 + table_c6
        table_c4.combinable_resource_ids = table_c2 + table_c6
        table_c6.combinable_resource_ids = table_c2 + table_c4

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots("UTC")
            resource_slots_c1 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=3
            )
            resource_slots_c3 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=4
            )
            resource_slots_c4 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=6
            )
            resource_slots_c6 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=9
            )
            resource_slots_c9 = self._filter_appointment_slots(slots)
        available_resources_c1 = [
            resource["id"] for resource in resource_slots_c1[0]["available_resources"]
        ]
        available_resources_c3 = [
            resource["id"] for resource in resource_slots_c3[0]["available_resources"]
        ]
        available_resources_c4 = [
            resource["id"] for resource in resource_slots_c4[0]["available_resources"]
        ]
        available_resources_c6 = [
            resource["id"] for resource in resource_slots_c6[0]["available_resources"]
        ]
        available_resources_c9 = [
            resource["id"] for resource in resource_slots_c9[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_c1, table_c2.ids)
        self.assertListEqual(
            available_resources_c3,
            table_c4.ids,
            "The table for 4 should be selected here as it's linked to the table for 2 and we don't want to lose capacity with a combination",
        )
        self.assertListEqual(available_resources_c4, table_c4.ids)
        self.assertListEqual(available_resources_c6, table_c6.ids)
        self.assertListEqual(available_resources_c9, (table_c4 + table_c6).ids)

        table_c4.booking_sequence = 1
        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots("UTC")
            resource_slots_c1 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=3
            )
            resource_slots_c3 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=4
            )
            resource_slots_c4 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=6
            )
            resource_slots_c6 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=9
            )
            resource_slots_c9 = self._filter_appointment_slots(slots)
        available_resources_c1 = [
            resource["id"] for resource in resource_slots_c1[0]["available_resources"]
        ]
        available_resources_c3 = [
            resource["id"] for resource in resource_slots_c3[0]["available_resources"]
        ]
        available_resources_c4 = [
            resource["id"] for resource in resource_slots_c4[0]["available_resources"]
        ]
        available_resources_c6 = [
            resource["id"] for resource in resource_slots_c6[0]["available_resources"]
        ]
        available_resources_c9 = [
            resource["id"] for resource in resource_slots_c9[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_c1, table_c4.ids)
        self.assertListEqual(available_resources_c3, table_c4.ids)
        self.assertListEqual(available_resources_c4, table_c4.ids)
        self.assertListEqual(available_resources_c6, table_c6.ids)
        self.assertListEqual(available_resources_c9, (table_c4 + table_c6).ids)

    @users("apt_manager")
    def test_appointment_resources_combinable_avoid_losing_extra_capacity(self):
        """Check that we don't lose capacity with the resource selected.
        If a capacity needed is greater than the capacity of the resource initially selected
        we should check if the linked resources of the one selected are not a better fit to avoid losing capacity.
        """

        nordic, scandinavian, snow = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 4,
                    "name": "Nordic",
                    "booking_sequence": 2,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 8,
                    "name": "Scandinavian",
                    "booking_sequence": 3,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 6,
                    "name": "Snow",
                    "booking_sequence": 4,
                },
            ]
        )

        nordic.combinable_resource_ids = scandinavian

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
        resource_slots_c5 = self._filter_appointment_slots(slots)
        available_resources_c5 = [
            resource["id"] for resource in resource_slots_c5[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_c5, scandinavian.ids)

        snow.booking_sequence = 1
        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
        resource_slots_c5 = self._filter_appointment_slots(slots)
        available_resources_c5 = [
            resource["id"] for resource in resource_slots_c5[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_c5, snow.ids)

        snow.booking_sequence = 4
        scandinavian.write(
            {
                "combinable_resource_ids": [(4, nordic.id)],
                "booking_sequence": 1,
            }
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
            resource_slots_c5 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=2
            )
            resource_slots_c2 = self._filter_appointment_slots(slots)
        available_resources_c5 = [
            resource["id"] for resource in resource_slots_c5[0]["available_resources"]
        ]
        available_resources_c2 = [
            resource["id"] for resource in resource_slots_c2[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_c5, scandinavian.ids)
        self.assertListEqual(available_resources_c2, scandinavian.ids)

    @users("apt_manager")
    def test_appointment_resources_combinable_complex(self):
        """Check resources assignation when the linked resources are not mirrored for all resources"""

        table1_c2, table2_c2, table3_c2 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 2,
                    "name": "Table 2A",
                    "booking_sequence": 1,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 2,
                    "name": "Table 2B",
                    "booking_sequence": 3,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 2,
                    "name": "Table 2C",
                    "booking_sequence": 2,
                },
            ]
        )
        table1_c2.combinable_resource_ids = table2_c2 + table3_c2
        table2_c2.combinable_resource_ids = table1_c2 + table3_c2
        table3_c2.combinable_resource_ids = table1_c2 + table2_c2

        table_c3 = self.env["resource.resource"].create(
            {
                "resource_type": "material",
                "appointment_type_ids": self.apt_type_resource.ids,
                "capacity": 3,
                "name": "Table 3A",
                "booking_sequence": 4,
            }
        )

        table1_c6, table2_c6 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 6,
                    "name": "Table 6A",
                    "booking_sequence": 5,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 6,
                    "name": "Table 6B",
                    "booking_sequence": 6,
                },
            ]
        )

        table1_c6.combinable_resource_ids = table_c3
        table2_c6.combinable_resource_ids = table1_c2 + table2_c2 + table3_c2

        table1_c8, table2_c8, bar = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 8,
                    "name": "Table 8A",
                    "booking_sequence": 8,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 8,
                    "name": "Table 8B",
                    "booking_sequence": 9,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 10,
                    "name": "Bar",
                    "booking_sequence": 15,
                    "booking_exclusive": False,
                },
            ]
        )
        table1_c8.booking_sequence = 10
        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=4
            )
            resource_slots_c4 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=8
            )
            resource_slots_c8 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=10
            )
            resource_slots_c10 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=12
            )
            resource_slots_c12 = self._filter_appointment_slots(slots)
        available_resources_c4 = [
            resource["id"] for resource in resource_slots_c4[0]["available_resources"]
        ]
        available_resources_c8 = [
            resource["id"] for resource in resource_slots_c8[0]["available_resources"]
        ]
        available_resources_c10 = [
            resource["id"] for resource in resource_slots_c10[0]["available_resources"]
        ]
        available_resources_c12 = [
            resource["id"] for resource in resource_slots_c12[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_c4, (table1_c2 + table3_c2).ids)
        self.assertListEqual(available_resources_c8, table2_c8.ids)
        self.assertListEqual(available_resources_c10, bar.ids)
        self.assertListEqual(
            available_resources_c12,
            (table2_c6 + table2_c6.combinable_resource_ids).sorted("booking_sequence").ids,
        )

    @users("apt_manager")
    def test_appointment_resources_combinable_last_availability(self):
        """Check that the last resource available is correctly computed with linked resources"""
        table_c2, table_c3 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 2,
                    "name": "Table for 2",
                    "booking_sequence": 1,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 3,
                    "name": "Table for 3",
                    "booking_sequence": 2,
                },
            ]
        )
        table_c2.combinable_resource_ids = table_c3

        # Create a booking for the first resource for all its capacity
        start = datetime(2022, 2, 14, 15, 0, 0)
        end = start + timedelta(hours=1)
        self.env["calendar.event"].with_context(self._test_context).create(
            {
                "appointment_type_id": self.apt_type_resource.id,
                "booking_line_ids": [
                    (
                        0,
                        0,
                        {
                            "resource_id": table_c2.id,
                            "capacity_reserved": 2,
                            "capacity_used": 2,
                        },
                    )
                ],
                "name": "Booking 1",
                "start": start,
                "stop": end,
            }
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=2
            )
            resource_slots_c2 = self._filter_appointment_slots(slots)
        available_resources_c2 = [
            resource["id"] for resource in resource_slots_c2[0]["available_resources"]
        ]
        self.assertEqual(
            set(available_resources_c2),
            set(table_c3.ids),
            "Only the table for 3 should be available as the other is booked",
        )
        self._test_slot_generate_available_resources(
            self.apt_type_resource,
            2,
            "UTC",
            start,
            end,
            table_c3,
            available_resources_c2,
            reference_date=self.reference_now,
        )

    @users("apt_manager")
    def test_appointment_resources_combinable_performance(self):
        """Simple use case of appointment type with combinable resources"""
        appointment = self.env["appointment.type"].create(
            {
                "appointment_tz": "UTC",
                "is_auto_assign": True,
                "min_schedule_hours": 1.0,
                "max_schedule_days": 8,
                "name": "Test",
                "manage_capacity": True,
                "schedule_based_on": "resources",
                "slot_ids": [
                    (
                        0,
                        0,
                        {
                            "weekday": str(self.reference_monday.isoweekday()),
                            "start_hour": 6,
                            "end_hour": 18,
                        },
                    )
                ],
            }
        )

        table1_c2, table2_c2, table3_c2 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": appointment.ids,
                    "capacity": 2,
                    "name": "Table %s - 2" % (i + 1),
                }
                for i in range(3)
            ]
        )

        table1_c4, table2_c4, table3_c4 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": appointment.ids,
                    "capacity": 4,
                    "name": "Table %s - 4" % (i + 1),
                }
                for i in range(3)
            ]
        )

        table1_c6 = self.env["resource.resource"].create(
            {
                "resource_type": "material",
                "appointment_type_ids": appointment.ids,
                "capacity": 6,
                "name": "Table - 6",
            }
        )

        (table1_c4 + table2_c4 + table3_c4).combinable_resource_ids = (
            table1_c2 + table2_c2 + table3_c2 + table1_c6
        )
        (table1_c2 + table2_c2 + table3_c2).combinable_resource_ids = (
            table1_c4 + table2_c4 + table3_c4
        )
        table1_c6.combinable_resource_ids = table1_c4 + table2_c4 + table3_c4

        # Flush everything, notably tracking values, as it may impact performances
        self.flush_tracking()

        with freeze_time(self.reference_now):
            appointment._get_appointment_slots("UTC")  # warm-up
            with self.assertQueryCount(default=4):
                slots = appointment._get_appointment_slots("UTC")
            resource_slots = self._filter_appointment_slots(
                slots,
                filter_weekdays=[0],
            )
            table1_c2_slots = self._filter_appointment_slots(
                slots,
                filter_weekdays=[0],
                filter_resources=table1_c2,
            )
            self.assertTrue(len(resource_slots) > 0)
            self.assertEqual(len(resource_slots), len(table1_c2_slots))
            with self.assertQueryCount(default=4):
                slots = appointment._get_appointment_slots("UTC", asked_capacity=5)
            resource_slots = self._filter_appointment_slots(
                slots,
                filter_weekdays=[0],
            )
            table1_c2_slots = self._filter_appointment_slots(
                slots,
                filter_weekdays=[0],
                filter_resources=table1_c2,
            )
            table1_c2_c4_slots = self._filter_appointment_slots(
                slots,
                filter_weekdays=[0],
                filter_resources=(table1_c2 + table1_c4),
            )
            self.assertTrue(len(resource_slots) > 0)
            self.assertEqual(len(table1_c2_slots), 0)
            self.assertEqual(len(resource_slots), len(table1_c2_c4_slots))

    @users("apt_manager")
    def test_appointment_resources_combinable_with_manual_date_first(self):
        """Check available linked resources with 'manual' assignment and 'date' selected first"""
        table_c2, table_c3 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 2,
                    "name": "Table for 2",
                    "booking_sequence": 1,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 3,
                    "name": "Table for 3",
                    "booking_sequence": 2,
                },
            ]
        )
        table_c2.combinable_resource_ids = table_c3
        self.apt_type_resource.write(
            {
                "is_auto_assign": False,
                "is_date_first": True,
            }
        )

        start = datetime(2022, 2, 14, 15, 0, 0)
        end = start + timedelta(hours=1)

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=2
            )
            resource_slots_c2 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
            resource_slots_c5 = self._filter_appointment_slots(slots)
        available_resources_c2 = [
            resource["id"] for resource in resource_slots_c2[0]["available_resources"]
        ]
        available_resources_c5 = [
            resource["id"] for resource in resource_slots_c5[0]["available_resources"]
        ]
        self.assertEqual(
            set(available_resources_c2),
            set((table_c2 + table_c3).ids),
            "Both resources should be available as the asked capacity is available in both",
        )
        self._test_slot_generate_available_resources(
            self.apt_type_resource,
            2,
            "UTC",
            start,
            end,
            table_c2 + table_c3,
            available_resources_c2,
            reference_date=self.reference_now,
        )
        self.assertEqual(
            set(available_resources_c5),
            set((table_c2 + table_c3).ids),
            "Both resources should be available as the asked capacity correspond to the remaining total",
        )
        self._test_slot_generate_available_resources(
            self.apt_type_resource,
            5,
            "UTC",
            start,
            end,
            table_c2 + table_c3,
            available_resources_c5,
            reference_date=self.reference_now,
        )

        # Create a booking for the first resource
        self.env["calendar.event"].with_context(self._test_context).create(
            {
                "appointment_type_id": self.apt_type_resource.id,
                "booking_line_ids": [
                    (
                        0,
                        0,
                        {
                            "resource_id": table_c2.id,
                            "capacity_reserved": 1,
                            "capacity_used": 1,
                        },
                    )
                ],
                "name": "Booking 1",
                "start": start,
                "stop": end,
            }
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=2
            )
            resource_slots_c2 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
            resource_slots_c5 = self._filter_appointment_slots(slots)
        available_resources_c2 = [
            resource["id"] for resource in resource_slots_c2[0]["available_resources"]
        ]
        self.assertEqual(
            set(available_resources_c2),
            set(table_c3.ids),
            "Only the table for 3 should be remaining as the other is booked",
        )
        self._test_slot_generate_available_resources(
            self.apt_type_resource,
            2,
            "UTC",
            start,
            end,
            table_c3,
            available_resources_c2,
            reference_date=self.reference_now,
        )
        self.assertEqual(
            len(resource_slots_c5),
            0,
            "There should not be enough availability for the asked capacity",
        )

    @users("apt_manager")
    def test_appointment_resources_sequence(self):
        """Check that the sequence is correctly taken into account when selecting resources for slots"""

        resource_1, resource_2 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 4,
                    "name": "Resource 1",
                    "booking_sequence": 5,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 10,
                    "name": "Resource 2",
                    "booking_sequence": 10,
                },
            ]
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots("UTC")
            resource_slots_c1 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=4
            )
            resource_slots_c4 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=6
            )
            resource_slots_c6 = self._filter_appointment_slots(slots)
        available_resources_c1 = [
            resource["id"] for resource in resource_slots_c1[0]["available_resources"]
        ]
        available_resources_c4 = [
            resource["id"] for resource in resource_slots_c4[0]["available_resources"]
        ]
        available_resources_c6 = [
            resource["id"] for resource in resource_slots_c6[0]["available_resources"]
        ]
        self.assertTrue(len(resource_slots_c1) > 0)
        self.assertListEqual(available_resources_c1, resource_1.ids)
        self.assertTrue(len(resource_slots_c4) > 0)
        self.assertListEqual(available_resources_c4, resource_1.ids)
        self.assertTrue(len(resource_slots_c6) > 0)
        self.assertListEqual(available_resources_c6, resource_2.ids)

        resource_2.booking_sequence = 1
        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots("UTC")
            resource_slots_c1 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=4
            )
            resource_slots_c4 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=6
            )
            resource_slots_c6 = self._filter_appointment_slots(slots)
        available_resources_c1 = [
            resource["id"] for resource in resource_slots_c1[0]["available_resources"]
        ]
        available_resources_c4 = [
            resource["id"] for resource in resource_slots_c4[0]["available_resources"]
        ]
        available_resources_c6 = [
            resource["id"] for resource in resource_slots_c6[0]["available_resources"]
        ]
        self.assertTrue(len(resource_slots_c1) > 0)
        self.assertListEqual(available_resources_c1, resource_2.ids)
        self.assertTrue(len(resource_slots_c4) > 0)
        self.assertListEqual(available_resources_c4, resource_1.ids)
        self.assertTrue(len(resource_slots_c6) > 0)
        self.assertListEqual(available_resources_c6, resource_2.ids)

    @users("apt_manager")
    def test_bookable_resources_shared(self):
        """Check shareable resources are correctly used"""

        resource, resource_shared = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 5,
                    "name": "Resource",
                    "booking_sequence": 5,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 10,
                    "name": "Resource Shareable",
                    "booking_sequence": 10,
                    "booking_exclusive": False,
                },
            ]
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=4
            )
            resource_slots_c4 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=6
            )
            resource_slots_c6 = self._filter_appointment_slots(slots)
        available_resources_c4 = [
            resource["id"] for resource in resource_slots_c4[0]["available_resources"]
        ]
        available_resources_c6 = [
            resource["id"] for resource in resource_slots_c6[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_c4, resource.ids)
        self.assertListEqual(available_resources_c6, resource_shared.ids)

        start = datetime(2022, 2, 14, 15, 0, 0)
        end = start + timedelta(hours=1)
        self.env["calendar.event"].with_context(self._test_context).create(
            [
                {
                    "appointment_type_id": self.apt_type_resource.id,
                    "booking_line_ids": [
                        (
                            0,
                            0,
                            {
                                "resource_id": resource_shared.id,
                                "capacity_reserved": 4,
                                "capacity_used": 4,
                            },
                        )
                    ],
                    "name": "Booking 1",
                    "start": start,
                    "stop": end,
                },
                {
                    "appointment_type_id": self.apt_type_resource.id,
                    "booking_line_ids": [
                        (
                            0,
                            0,
                            {
                                "resource_id": resource_shared.id,
                                "capacity_reserved": 2,
                                "capacity_used": 2,
                            },
                        )
                    ],
                    "name": "Booking 2",
                    "start": start,
                    "stop": end,
                },
            ]
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=4
            )
            resource_slots_c4 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
            resource_slots_c5 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=6
            )
            resource_slots_c6 = self._filter_appointment_slots(slots)
        available_resources_c4 = [
            resource["id"] for resource in resource_slots_c4[0]["available_resources"]
        ]
        available_resources_c5 = [
            resource["id"] for resource in resource_slots_c5[0]["available_resources"]
        ]
        available_resources_c6 = resource_slots_c6 and [
            resource["id"] for resource in resource_slots_c6[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_c4, resource.ids)
        self.assertListEqual(available_resources_c5, resource.ids)
        self.assertListEqual(available_resources_c6, [])

        resource_shared.booking_sequence = 1
        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=4
            )
            resource_slots_c4 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
            resource_slots_c5 = self._filter_appointment_slots(slots)
        available_resources_c4 = [
            resource["id"] for resource in resource_slots_c4[0]["available_resources"]
        ]
        available_resources_c5 = [
            resource["id"] for resource in resource_slots_c5[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_c4, resource_shared.ids)
        self.assertListEqual(available_resources_c5, resource.ids)

    @users("apt_manager")
    def test_bookable_resources_shared_combined_with_capacity(self):
        """Check that resources shareable linked together with the capacity management
        correctly compute the remaining capacity"""

        resource_1, resource_2 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 5,
                    "name": "Resource 1",
                    "booking_sequence": 5,
                    "booking_exclusive": False,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 6,
                    "name": "Resource 2",
                    "booking_sequence": 10,
                    "booking_exclusive": False,
                },
            ]
        )

        resource_1.combinable_resource_ids = resource_2

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
            resource_slots_c5 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=7
            )
            resource_slots_c7 = self._filter_appointment_slots(slots)
        available_resources_c5 = [
            resource["id"] for resource in resource_slots_c5[0]["available_resources"]
        ]
        available_resources_c7 = [
            resource["id"] for resource in resource_slots_c7[0]["available_resources"]
        ]
        self.assertListEqual(
            available_resources_c5,
            resource_1.ids,
            "Should pick the first resource as it's a best match",
        )
        self.assertListEqual(
            available_resources_c7,
            (resource_1 + resource_2).ids,
            "Should pick both resources as asked capacity exceeds each resource capacity",
        )

        # Create a booking for the first resource for all its capacity
        start = datetime(2022, 2, 14, 15, 0, 0)
        end = start + timedelta(hours=1)
        self.env["calendar.event"].with_context(self._test_context).create(
            {
                "appointment_type_id": self.apt_type_resource.id,
                "booking_line_ids": [
                    (
                        0,
                        0,
                        {
                            "resource_id": resource_1.id,
                            "capacity_reserved": 5,
                            "capacity_used": 5,
                        },
                    )
                ],
                "name": "Booking 1",
                "start": start,
                "stop": end,
            }
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
            resource_slots_c5 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=7
            )
            resource_slots_c7 = self._filter_appointment_slots(slots)
        available_resources_c5 = [
            resource["id"] for resource in resource_slots_c5[0]["available_resources"]
        ]
        self.assertListEqual(
            available_resources_c5,
            resource_2.ids,
            "Should pick the second resource as the first one is already taken",
        )
        self.assertEqual(
            len(resource_slots_c7),
            0,
            "There should not be enough capacity remaining for the asked capacity",
        )

    @users("apt_manager")
    def test_bookable_resources_shared_performance(self):
        """Simple use case with shareable resources"""
        appointment = self.env["appointment.type"].create(
            {
                "appointment_tz": "UTC",
                "is_auto_assign": True,
                "min_schedule_hours": 1.0,
                "max_schedule_days": 8,
                "name": "Test",
                "manage_capacity": True,
                "schedule_based_on": "resources",
                "slot_ids": [
                    (
                        0,
                        0,
                        {
                            "weekday": str(self.reference_monday.isoweekday()),
                            "start_hour": 6,
                            "end_hour": 18,
                        },
                    )
                ],
            }
        )

        self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": appointment.ids,
                    "capacity": 5,
                    "name": "Resource %s" % i,
                    "booking_exclusive": False,
                }
                for i in range(20)
            ]
        )
        # Flush everything, notably tracking values, as it may impact performances
        self.flush_tracking()

        with freeze_time(self.reference_now):
            appointment._get_appointment_slots("UTC")  # warm-up
            with self.assertQueryCount(default=4):
                appointment._get_appointment_slots("UTC")

    @users("apt_manager")
    def test_appointment_resources_restrict_resources(self):
        """Check that resources restricted on slots are taken into account"""
        appointment = self.env[
            "appointment.type"
        ].create(
            {
                "appointment_tz": "UTC",
                "is_auto_assign": False,
                "is_date_first": True,  # easier to check all resources available for each slot
                "min_schedule_hours": 1.0,
                "max_schedule_days": 5,
                "name": "Test",
                "manage_capacity": True,
                "schedule_based_on": "resources",
                "slot_ids": [
                    (
                        0,
                        0,
                        {
                            "weekday": str(self.reference_monday.isoweekday()),
                            "start_hour": 15,
                            "end_hour": 16,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "weekday": str(self.reference_monday.isoweekday() + 1),
                            "start_hour": 15,
                            "end_hour": 16,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "weekday": str(self.reference_monday.isoweekday() + 2),
                            "start_hour": 15,
                            "end_hour": 16,
                        },
                    ),
                ],
            }
        )

        resource1, resource2, resource3 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": appointment.ids,
                    "name": "Resource %s" % i,
                }
                for i in range(3)
            ]
        )

        appointment.slot_ids[0].restrict_to_resource_ids = resource1.ids
        appointment.slot_ids[1].restrict_to_resource_ids = (resource2 + resource3).ids

        with freeze_time(self.reference_now):
            slots = appointment._get_appointment_slots("UTC")
        monday_slots = self._filter_appointment_slots(slots, filter_weekdays=[0])
        tuesday_slots = self._filter_appointment_slots(slots, filter_weekdays=[1])
        wednesday_slots = self._filter_appointment_slots(slots, filter_weekdays=[2])
        available_resources_monday = [
            resource["id"] for resource in monday_slots[0]["available_resources"]
        ]
        available_resources_tuesday = [
            resource["id"] for resource in tuesday_slots[0]["available_resources"]
        ]
        available_resources_wednesday = [
            resource["id"] for resource in wednesday_slots[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_monday, resource1.ids)
        self.assertListEqual(available_resources_tuesday, (resource2 + resource3).ids)
        self.assertListEqual(
            available_resources_wednesday, (resource1 + resource2 + resource3).ids
        )

        # Custom Appointment
        appointment.slot_ids = False
        appointment.update(
            {
                "category": "custom",
                "slot_ids": [
                    Command.create(
                        {
                            "start_datetime": self.reference_monday,
                            "end_datetime": self.reference_monday + timedelta(hours=1),
                        }
                    ),
                    Command.create(
                        {
                            "start_datetime": self.reference_monday + timedelta(days=1),
                            "end_datetime": self.reference_monday
                            + timedelta(days=1, hours=1),
                        }
                    ),
                    Command.create(
                        {
                            "start_datetime": self.reference_monday + timedelta(days=2),
                            "end_datetime": self.reference_monday
                            + timedelta(days=2, hours=1),
                        }
                    ),
                ],
            }
        )

        appointment.slot_ids[0].restrict_to_resource_ids = resource1.ids
        appointment.slot_ids[1].restrict_to_resource_ids = (resource2 + resource3).ids
        with freeze_time(self.reference_now):
            slots = appointment._get_appointment_slots("UTC")

        monday_slots = self._filter_appointment_slots(slots, filter_weekdays=[0])
        tuesday_slots = self._filter_appointment_slots(slots, filter_weekdays=[1])
        wednesday_slots = self._filter_appointment_slots(slots, filter_weekdays=[2])
        available_resources_monday = [
            resource["id"] for resource in monday_slots[0]["available_resources"]
        ]
        available_resources_tuesday = [
            resource["id"] for resource in tuesday_slots[0]["available_resources"]
        ]
        available_resources_wednesday = [
            resource["id"] for resource in wednesday_slots[0]["available_resources"]
        ]
        self.assertListEqual(available_resources_monday, resource1.ids)
        self.assertListEqual(available_resources_tuesday, (resource2 + resource3).ids)
        self.assertListEqual(
            available_resources_wednesday, (resource1 + resource2 + resource3).ids
        )

    @users("apt_manager")
    def test_appointment_resources_assign_manual_date_first(self):
        """Check that all resources are available with 'manual' assignment and 'date' selected first"""
        self.apt_type_resource.write(
            {
                "is_auto_assign": False,
                "is_date_first": True,
            }
        )

        nordic, scandinavian, snow = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 4,
                    "name": "Nordic",
                    "booking_sequence": 2,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 8,
                    "name": "Scandinavian",
                    "booking_sequence": 3,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 6,
                    "name": "Snow",
                    "booking_sequence": 4,
                },
            ]
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots("UTC")
            available_resources_c1 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=4
            )
            available_resources_c4 = self._filter_appointment_slots(slots)
            slots = self.apt_type_resource._get_appointment_slots(
                "UTC", asked_capacity=5
            )
            available_resources_c5 = self._filter_appointment_slots(slots)
        available_resources_c1 = [
            resource["id"]
            for resource in available_resources_c1[0]["available_resources"]
        ]
        available_resources_c4 = [
            resource["id"]
            for resource in available_resources_c4[0]["available_resources"]
        ]
        available_resources_c5 = [
            resource["id"]
            for resource in available_resources_c5[0]["available_resources"]
        ]
        self.assertListEqual(
            available_resources_c1,
            (nordic + scandinavian + snow).ids,
            "All resources should be available with asked_capacity=1",
        )
        self.assertListEqual(
            available_resources_c4,
            (nordic + scandinavian + snow).ids,
            "All resources should be available, the perfect matches are ignored with manual assignment and date first",
        )
        self.assertListEqual(available_resources_c5, (scandinavian + snow).ids)

    @users("apt_manager")
    def test_appointment_resources_booked_for_all_appointments(self):
        """Check that a resource can only be booked once, even if shared among appointment_types"""
        paddle_court = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 1,
                    "name": "Paddle Court",
                }
            ]
        )
        self.apt_type_resource_2 = self.apt_type_resource.copy()

        # Assert initial data
        with freeze_time(self.reference_now):
            slots = self.apt_type_resource_2._get_appointment_slots("UTC")
            resource_slots = self._filter_appointment_slots(slots)
            self.assertEqual(len(resource_slots), 1)

        # Resource is booked on its slot on appointment_type_resource
        self.env["calendar.event"].with_context(self._test_context).create(
            {
                "appointment_type_id": self.apt_type_resource.id,
                "booking_line_ids": [
                    (
                        0,
                        0,
                        {
                            "resource_id": paddle_court.id,
                            "capacity_reserved": 1,
                            "capacity_used": paddle_court.capacity,
                        },
                    )
                ],
                "name": "Booking 1",
                "start": datetime(2022, 2, 14, 15, 0, 0),
                "stop": datetime(2022, 2, 14, 15, 0, 0) + timedelta(hours=1),
            }
        )

        # Check other appointment_type availabilities
        with freeze_time(self.reference_now):
            slots = self.apt_type_resource_2._get_appointment_slots("UTC")
            resource_slots = self._filter_appointment_slots(slots)

        self.assertEqual(
            len(resource_slots),
            0,
            "Once a resource is booked on a slot, it should not be available anymore to other appointment types.",
        )

    def test_appointment_resources_dont_skip_mail_user_not_attendee(self):
        # Resource is booked on its slot on appointment_type_resource
        event = (
            self.env["calendar.event"]
            .with_context(self._test_context)
            .create(
                {
                    "appointment_type_id": self.apt_type_resource.id,
                    "name": "Booking 1",
                    "start": datetime(2022, 2, 14, 15, 0, 0),
                    "stop": datetime(2022, 2, 14, 15, 0, 0) + timedelta(hours=1),
                }
            )
        )

        self.assertFalse(event._skip_send_mail_status_update())

    @users("apt_manager")
    def test_appointment_resources_multi_edit_capacity(self):
        """Check that the capacity reserved is correctly updated in multi-edit"""
        resource_1, resource_2 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 4,
                    "name": "Table of 4",
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 3,
                    "name": "Table of 3",
                },
            ]
        )
        resource_1.combinable_resource_ids = resource_2
        start = datetime(2022, 2, 14, 15, 0, 0)
        end = start + timedelta(hours=1)
        apt_1, apt_2 = (
            self.env["calendar.event"]
            .with_context(self._test_context)
            .create(
                [
                    {
                        "appointment_type_id": self.apt_type_resource.id,
                        "booking_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "resource_id": resource_1.id,
                                    "capacity_reserved": 4,
                                    "capacity_used": 4,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "resource_id": resource_2.id,
                                    "capacity_reserved": 1,
                                    "capacity_used": 3,
                                },
                            ),
                        ],
                        "name": "Booking 1",
                        "start": start,
                        "stop": end,
                    },
                    {
                        "appointment_type_id": self.apt_type_resource.id,
                        "booking_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "resource_id": resource_1.id,
                                    "capacity_reserved": 4,
                                    "capacity_used": 2,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "resource_id": resource_2.id,
                                    "capacity_reserved": 2,
                                    "capacity_used": 3,
                                },
                            ),
                        ],
                        "name": "Booking 1",
                        "start": start + timedelta(hours=2),
                        "stop": end + timedelta(hours=2),
                    },
                ]
            )
        )
        self.assertEqual(apt_1.total_capacity_reserved, 5)
        self.assertEqual(apt_2.total_capacity_reserved, 6)

        (apt_1 + apt_2).write({"total_capacity_reserved": 7})
        # Every appointment should be updated with the new value
        self.assertEqual(apt_1.total_capacity_reserved, 7)
        self.assertEqual(apt_2.total_capacity_reserved, 7)

    @users("apt_manager")
    def test_appointment_resources_with_resource_calendar(self):
        """Check that the slots correctly take into account the default resource calendar"""
        self.env["resource.resource"].create(
            {
                "resource_type": "material",
                "appointment_type_ids": self.apt_type_resource.ids,
                "name": "Resource",
                "calendar_id": self.env.ref(
                    "calendar.appointment_default_resource_calendar"
                ).id,
            }
        )
        self.apt_type_resource.slot_ids.write({"start_hour": 8})

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots("UTC")
        self.assertSlots(
            slots,
            [
                {
                    "name_formated": "February 2022",
                    "month_date": datetime(2022, 2, 1),
                    "weeks_count": 5,  # 31/01 -> 28/02 (06/03)
                }
            ],
            {
                "enddate": self.global_slots_enddate,
                "startdate": self.reference_now_monthweekstart,
                "slots_start_hours": list(range(8, 16)),  # 8 AM => 4 PM
                "slots_startdate": self.reference_monday.date(),  # first Monday after reference_now
                "slots_enddate": self.reference_monday.date(),  # only test that day
            },
        )

    @users("apt_manager")
    def test_appointment_resources_duplicate(self):
        """Check that we can correctly duplicate resource bookings"""
        table, other_table = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 3,
                    "name": "Table for 3",
                    "booking_sequence": 1,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 4,
                    "name": "Table for 4",
                    "booking_sequence": 2,
                },
            ]
        )

        start = datetime(2022, 2, 14, 15, 0, 0)
        end = start + timedelta(hours=1)
        booking = (
            self.env["calendar.event"]
            .with_context(self._test_context)
            .create(
                {
                    "appointment_type_id": self.apt_type_resource.id,
                    "booking_line_ids": [
                        (
                            0,
                            0,
                            {
                                "resource_id": table.id,
                                "capacity_reserved": 2,
                                "capacity_used": 3,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "resource_id": other_table.id,
                                "capacity_reserved": 3,
                                "capacity_used": 4,
                            },
                        ),
                    ],
                    "name": "Resource booking",
                    "start": start,
                    "stop": end,
                }
            )
        )

        duplicate = booking.copy()
        self.assertEqual(
            booking.name,
            duplicate.name,
            "Resource booking should have duplicated correctly",
        )
        self.assertListEqual(
            booking.resource_ids.ids,
            duplicate.resource_ids.ids,
            "Resources should be the same",
        )
        self.assertEqual(
            booking.total_capacity_used,
            duplicate.total_capacity_used,
            "Capacity used should be the same",
        )
        self.assertEqual(
            booking.total_capacity_reserved,
            duplicate.total_capacity_reserved,
            "Capacity reserved should be the same",
        )
        self.assertListEqual(
            [bl.capacity_reserved for bl in booking.booking_line_ids],
            [bl.capacity_reserved for bl in duplicate.booking_line_ids],
            "Capacity reserved should be the same for each booking line",
        )

    @users("apt_manager")
    def test_appointment_resources_without_capacity_management(self):
        """Check use case where capacity management is not activated"""

        self.apt_type_resource.manage_capacity = False

        resource_1, resource_2, resource_3 = self.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 6,
                    "name": "Resource 1",
                    "booking_sequence": 1,
                    "booking_exclusive": False,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 4,
                    "name": "Resource 2",
                    "booking_sequence": 2,
                },
                {
                    "appointment_type_ids": self.apt_type_resource.ids,
                    "capacity": 1,
                    "name": "Resource 3",
                    "booking_sequence": 3,
                },
            ]
        )

        resource_2.combinable_resource_ids = resource_3

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots("UTC")
        resource_slots = self._filter_appointment_slots(slots)
        available_resources = [
            resource["id"] for resource in resource_slots[0]["available_resources"]
        ]
        self.assertListEqual(available_resources, resource_1.ids)

        start = datetime(2022, 2, 14, 15, 0, 0)
        end = start + timedelta(hours=1)
        booking = (
            self.env["calendar.event"]
            .with_context(self._test_context)
            .create(
                {
                    "appointment_type_id": self.apt_type_resource.id,
                    "booking_line_ids": [
                        (
                            0,
                            0,
                            {
                                "resource_id": resource_1.id,
                                "capacity_reserved": 1,
                                "capacity_used": resource_1.capacity,
                            },
                        )
                    ],
                    "name": "Booking 1",
                    "start": start,
                    "stop": end,
                }
            )
        )

        self.assertEqual(booking.booking_line_ids.capacity_reserved, 1)
        self.assertEqual(
            booking.booking_line_ids.capacity_used,
            1,
            "When we don't manage capacity, the bookings should use 1 capacity only.",
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots("UTC")
        resource_slots = self._filter_appointment_slots(slots)
        available_resources = [
            resource["id"] for resource in resource_slots[0]["available_resources"]
        ]
        self.assertListEqual(
            available_resources,
            resource_2.ids,
            "The first resource should now be unavailable and the second one is chosen",
        )

    @users("apt_manager")
    def test_generate_slots_until_midnight_resources(self):
        """Check end of day slot, e.g. 23:00-00:00 for a 1h duration"""

        self.apt_type_resource.appointment_duration = 1
        self.apt_type_resource.max_schedule_days = 1
        # 22:00-23:00 range in UTC will correspond to 23:00-00:00 in UTC+1.
        # So, this matches the attendance ending at midnight in the resource calendar.
        # The corresponding interval bound ends up as 22.59.999999 in UTC unavailabilities.
        self.env.ref(
            "calendar.appointment_default_resource_calendar"
        ).sudo().tz = "Europe/Brussels"
        self.apt_type_resource.slot_ids.write(
            {
                "start_hour": 22,
                "end_hour": 23,
            }
        )

        self.env["resource.resource"].create(
            {
                "resource_type": "material",
                "appointment_type_ids": self.apt_type_resource.ids,
                "name": "Resource",
                "calendar_id": self.env.ref(
                    "calendar.appointment_default_resource_calendar"
                ).id,
            }
        )

        with freeze_time(self.reference_now):
            slots = self.apt_type_resource._get_appointment_slots("UTC")
        self.assertSlots(
            slots,
            [
                {
                    "name_formated": "February 2022",
                    "month_date": datetime(2022, 2, 1),
                    "weeks_count": 5,  # 31/01 -> 28/02 (06/03)
                }
            ],
            {
                "enddate": self.global_slots_enddate,
                "startdate": self.reference_now_monthweekstart,
                "slots_start_hours": [22],
                "slots_startdate": self.reference_monday.date(),
                "slots_enddate": self.reference_monday.date(),
            },
        )


@tagged("appointment_resources", "post_install", "-at_install")
class AppointmentResourceLedgerTest(AppointmentCommon):
    """A booked resource is a claim in resource.reservation, like a booked person."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.managed, cls.unmanaged = cls.env["appointment.type"].create(
            [
                {
                    "appointment_tz": "UTC",
                    "name": "Managed",
                    "manage_capacity": True,
                    "schedule_based_on": "resources",
                },
                {
                    "appointment_tz": "UTC",
                    "name": "Unmanaged",
                    "manage_capacity": False,
                    "schedule_based_on": "resources",
                },
            ]
        )
        cls.table, cls.counter = cls.env["resource.resource"].create(
            [
                {
                    "appointment_type_ids": (cls.managed | cls.unmanaged).ids,
                    "capacity": 4,
                    "name": "Table of four",
                    "resource_type": "material",
                },
                {
                    "appointment_type_ids": cls.managed.ids,
                    "capacity": 10,
                    "name": "Bar counter",
                    "booking_exclusive": False,
                    "resource_type": "material",
                },
            ]
        )
        cls.start = datetime(2022, 2, 14, 12, 0, 0)
        cls.stop = cls.start + timedelta(hours=2)

    def _reservations(self, resource):
        return self.env["resource.reservation"].search(
            [("resource_id", "=", resource.id)]
        )

    def _book(self, appointment_type, resource, capacity_reserved=1):
        return self.env["calendar.event"].create(
            {
                "appointment_type_id": appointment_type.id,
                "booking_line_ids": [
                    Command.create(
                        {
                            "resource_id": resource.id,
                            "capacity_reserved": capacity_reserved,
                        }
                    )
                ],
                "name": "Booking",
                "start": self.start,
                "stop": self.stop,
            }
        )

    def test_capacity_lives_on_the_resource(self):
        self.assertEqual(self.table.capacity, 4)
        self.assertEqual(self.table.resource_type, "material")
        self.table.capacity = 6
        self.assertEqual(self.table.capacity, 6)
        self.table.capacity = 2
        self.assertEqual(self.table.capacity, 2)

    def test_an_exclusive_booking_takes_the_whole_resource(self):
        event = self._book(self.managed, self.table, capacity_reserved=2)
        reservation = self._reservations(self.table)
        self.assertEqual(len(reservation), 1)
        self.assertRecordValues(
            reservation,
            [
                {
                    "res_model": "calendar.event",
                    "res_id": event.id,
                    "date_start": self.start,
                    "date_end": self.stop,
                    "allocated_percentage": 100.0,
                    "enforcement_mode": "soft",
                }
            ],
        )

    def test_a_shared_booking_takes_its_share(self):
        self._book(self.managed, self.counter, capacity_reserved=3)
        self.assertEqual(self._reservations(self.counter).allocated_percentage, 30.0)

    def test_unmanaged_booking_takes_the_whole_resource(self):
        self._book(self.unmanaged, self.table, capacity_reserved=1)
        self.assertEqual(self._reservations(self.table).allocated_percentage, 100.0)

    def test_two_shared_bookings_over_capacity_conflict(self):
        first = self._book(self.managed, self.counter, capacity_reserved=6)
        second = self._book(self.managed, self.counter, capacity_reserved=6)
        (first | second).invalidate_recordset(["schedule_overlap_count"])
        self.assertEqual(first.schedule_overlap_count, 1)
        self.assertEqual(second.schedule_overlap_count, 1)

    def test_two_shared_bookings_within_capacity_do_not_conflict(self):
        first = self._book(self.managed, self.counter, capacity_reserved=4)
        second = self._book(self.managed, self.counter, capacity_reserved=4)
        (first | second).invalidate_recordset(["schedule_overlap_count"])
        self.assertEqual(first.schedule_overlap_count, 0)
        self.assertEqual(second.schedule_overlap_count, 0)

    def test_moving_or_cancelling_the_booking_moves_the_claim(self):
        event = self._book(self.managed, self.table)
        event.write(
            {
                "start": self.start + timedelta(days=1),
                "stop": self.stop + timedelta(days=1),
            }
        )
        self.assertEqual(
            self._reservations(self.table).date_start, self.start + timedelta(days=1)
        )
        event.booking_line_ids.write({"resource_id": self.counter.id})
        self.assertFalse(self._reservations(self.table))
        self.assertEqual(len(self._reservations(self.counter)), 1)
        event.booking_line_ids.unlink()
        self.assertFalse(self._reservations(self.counter))

    def test_cancelled_event_releases_the_resource(self):
        event = self._book(self.managed, self.table)
        event.action_archive()
        self.assertFalse(self._reservations(self.table))
        event.action_unarchive()
        self.assertEqual(len(self._reservations(self.table)), 1)

    def test_foreign_booking_uses_the_same_ceiling(self):
        self.env["resource.reservation"].create(
            {
                "name": "Other application",
                "resource_id": self.counter.id,
                "date_start": self.start,
                "date_end": self.stop,
            }
        )
        remaining = self.managed._get_resources_remaining_capacity(
            self.counter, self.start, self.stop
        )
        self.assertEqual(remaining[self.counter], 0)
        self.counter.booking_limit_percentage = 120
        remaining = self.managed._get_resources_remaining_capacity(
            self.counter, self.start, self.stop
        )
        self.assertEqual(remaining[self.counter], 2)

    def test_adjacent_bookings_use_peak_capacity(self):
        self._book(self.managed, self.counter, capacity_reserved=6)
        later = self._book(self.managed, self.counter, capacity_reserved=6)
        later.write({"start": self.stop, "stop": self.stop + timedelta(hours=2)})
        remaining = self.managed._get_resources_remaining_capacity(
            self.counter, self.start, self.stop + timedelta(hours=2)
        )
        self.assertEqual(remaining[self.counter], 4)

    def test_free_booking_releases_capacity_and_ledger(self):
        event = self._book(self.managed, self.counter, capacity_reserved=10)
        event.show_as = "free"
        self.assertEqual(event.booking_line_ids.capacity_used, 0)
        self.assertFalse(self._reservations(self.counter))
        remaining = self.managed._get_resources_remaining_capacity(
            self.counter, self.start, self.stop
        )
        self.assertEqual(remaining[self.counter], 10)

    def test_enforced_overbooking_survives_later_edits(self):
        self.counter.booking_limit_percentage = 120
        first = self._book(self.managed, self.counter, capacity_reserved=10)
        first.booking_capacity_enforced = True
        second = self._book(self.managed, self.counter, capacity_reserved=2)
        second.booking_capacity_enforced = True
        self.assertEqual(
            self._reservations(self.counter).mapped("booking_state"), ["over", "over"]
        )
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            second.booking_line_ids.capacity_reserved = 3

    def test_enforced_partial_booking_keeps_the_remaining_seats_available(self):
        event = self._book(self.managed, self.counter, capacity_reserved=5)
        event.booking_capacity_enforced = True
        start = self.start.replace(tzinfo=UTC)
        stop = self.stop.replace(tzinfo=UTC)
        values = self.managed._slot_availability_prepare_resources_leave_values(
            self.counter, start, stop
        )
        self.assertFalse(
            any(
                stop > start
                for start, stop in values["resource_unavailabilities"][self.counter]
            )
        )
        self.assertEqual(
            self.managed._get_resources_remaining_capacity(
                self.counter, self.start, self.stop
            )[self.counter],
            5,
        )

    def test_more_slots_do_not_add_occupancy_queries(self):
        slot = self.env["appointment.slot"].new({"weekday": "1"})
        start, stop = self.start.replace(tzinfo=UTC), self.stop.replace(tzinfo=UTC)

        def fill(count):
            slots = [
                {"UTC": (self.start, self.stop), "slot": slot} for _ in range(count)
            ]
            self.managed._slots_add_resources_availability(
                slots, start, stop, self.counter
            )
            self.assertTrue(all(item.get("available_resource_ids") for item in slots))

        fill(1)
        with self.capturedQueries() as single:
            fill(1)
        with self.capturedQueries() as many:
            fill(50)
        self.assertEqual(len(many), len(single))
