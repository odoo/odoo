"""Behavioral contracts for Calendar's meeting and public booking boundary."""

import runpy
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from lxml import html

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestUnifiedCalendarOccupancy(TransactionCase):
    def test_equipment_customers_do_not_reserve_staff_capacity(self):
        booker = new_test_user(self.env, "equipment_booker", groups="base.group_user")
        staff = self.env["resource.resource"].create(
            {
                "resource_type": "material",
                "name": "Equipment booker staff resource",
                "user_id": booker.id,
            }
        )
        profiles = self.env["resource.resource"].create(
            [
                {"name": "Equipment A"},
                {"name": "Equipment B"},
            ]
        )
        offer = self.env["appointment.type"].create(
            {
                "name": "Equipment booking",
                "schedule_based_on": "resources",
                "resource_ids": [Command.set(profiles.ids)],
            }
        )
        events = (
            self.env["calendar.event"]
            .with_context(no_mail_to_attendees=True)
            .create(
                [
                    {
                        "name": "Concurrent equipment reservation",
                        "start": self.start,
                        "stop": self.start + timedelta(hours=1),
                        "appointment_type_id": offer.id,
                        "appointment_booker_id": booker.partner_id.id,
                        "partner_ids": [Command.set(booker.partner_id.ids)],
                        "booking_capacity_enforced": True,
                        "booking_line_ids": [
                            Command.create(
                                {
                                    "resource_id": profile.id,
                                    "capacity_reserved": 1,
                                }
                            )
                        ],
                    }
                    for profile in profiles
                ]
            )
        )
        self.assertEqual(events.reservation_ids.resource_id, profiles)
        self.assertNotIn(staff, events.reservation_ids.resource_id)
        self.assertTrue(
            booker.partner_id._is_calendar_available(self.start, events[0].stop, offer)
        )
        self.assertFalse(
            booker.partner_id._get_busy_calendar_intervals(self.start, events[0].stop)
        )
        self.assertFalse(
            booker.partner_id.with_user(booker)._get_busy_calendar_intervals(
                self.start, events[0].stop
            )
        )
        self.assertEqual(events.attendee_ids.partner_id, booker.partner_id)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["calendar.event"].with_context(no_mail_to_attendees=True).create(
                {
                    "name": "Occupied equipment must still reject another booking",
                    "start": self.start,
                    "stop": events[0].stop,
                    "appointment_type_id": offer.id,
                    "appointment_booker_id": booker.partner_id.id,
                    "partner_ids": [Command.set(booker.partner_id.ids)],
                    "booking_capacity_enforced": True,
                    "booking_line_ids": [
                        Command.create(
                            {
                                "resource_id": profiles[0].id,
                                "capacity_reserved": 1,
                            }
                        )
                    ],
                }
            )
        stale = self.env["resource.reservation"].create(
            {
                "name": "Old customer attendance projection",
                "resource_id": staff.id,
                "res_model": "calendar.event",
                "res_id": events[0].id,
                "date_start": self.start,
                "date_end": events[0].stop,
                "allocated_percentage": 100,
            }
        )
        migrate = runpy.run_path(
            str(Path(__file__).parents[1] / "migrations/2.1/end-equipment-occupancy.py")
        )["migrate"]
        migrate(self.cr, "19.0.2.0")
        migrate(self.cr, "19.0.2.0")
        self.assertFalse(stale.exists())
        self.assertEqual(events.reservation_ids.resource_id, profiles)
        self.assertEqual(events.attendee_ids.partner_id, booker.partner_id)

    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {"name": "Civil-day attendee", "tz": "America/New_York"}
        )
        self.start = datetime(2035, 3, 15, 10)
        self.event = (
            self.env["calendar.event"]
            .with_context(no_mail_to_attendees=True)
            .create(
                {
                    "name": "Occupancy contract",
                    "start": self.start,
                    "stop": self.start + timedelta(hours=1),
                    "partner_ids": [Command.set(self.partner.ids)],
                }
            )
        )

    def test_boundaries_aware_instants_and_declined(self):
        busy = self.partner._get_busy_calendar_events
        self.assertFalse(busy(self.start - timedelta(hours=1), self.start))
        self.assertFalse(busy(self.event.stop, self.event.stop + timedelta(hours=1)))
        self.assertIn(self.event, busy(self.start, self.event.stop)[self.partner.id])
        offset = timezone(timedelta(hours=-6))
        self.assertIn(
            self.event,
            busy(
                self.start.replace(tzinfo=UTC).astimezone(offset),
                self.event.stop.replace(tzinfo=UTC).astimezone(offset),
            )[self.partner.id],
        )
        self.event.attendee_ids.filtered(
            lambda a: a.partner_id == self.partner
        ).state = "declined"
        self.assertFalse(busy(self.start, self.event.stop))

    def test_all_day_uses_civil_midnight(self):
        self.event.write(
            {"allday": True, "start_date": "2035-03-15", "stop_date": "2035-03-15"}
        )
        busy = self.partner._get_busy_calendar_events
        self.assertIn(
            self.event,
            busy(datetime(2035, 3, 15, 4), datetime(2035, 3, 15, 4, 30))[
                self.partner.id
            ],
        )
        self.assertFalse(busy(datetime(2035, 3, 15, 3), datetime(2035, 3, 15, 4)))
        self.assertFalse(busy(datetime(2035, 3, 16, 4), datetime(2035, 3, 16, 5)))
        self.event.show_as = "free"
        self.assertFalse(busy(datetime(2035, 3, 15, 7), datetime(2035, 3, 15, 8)))


@tagged("post_install", "-at_install")
class TestUnifiedCalendarAccess(HttpCase):
    def setUp(self):
        super().setUp()
        self.customer, self.guest = self.env["res.partner"].create(
            [
                {"name": "Booking customer", "email": "customer@example.test"},
                {"name": "Invited guest", "email": "guest@example.test"},
            ]
        )
        self.offer = self.env["appointment.type"].create(
            {
                "name": "Access contract",
                "staff_user_ids": [Command.link(self.env.user.id)],
            }
        )
        self.event = (
            self.env["calendar.event"]
            .with_context(no_mail_to_attendees=True)
            .create(
                {
                    "name": "Private booking contract",
                    "start": datetime(2035, 3, 15, 10),
                    "stop": datetime(2035, 3, 15, 11),
                    "privacy": "private",
                    "appointment_type_id": self.offer.id,
                    "appointment_booker_id": self.customer.id,
                    "partner_ids": [
                        Command.set(
                            (self.customer | self.guest | self.env.user.partner_id).ids
                        )
                    ],
                }
            )
        )
        self.event._update_access_token()
        self.guest_token = self.event.attendee_ids.filtered(
            lambda a: a.partner_id == self.guest
        ).access_token

    def test_conference_token_is_not_a_meeting_capability(self):
        for route in ("/calendar/view/{}", "/calendar/ics/{}.ics"):
            response = self.url_open(route.format(self.event.access_token))
            self.assertEqual(response.status_code, 404)
        self.assertTrue(self.event.active)

    def test_guest_cannot_impersonate_booker_or_learn_management_token(self):
        response = self.url_open(
            f"/calendar/view/{self.guest_token}?partner_id={self.customer.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.event.booking_access_token, response.text)
        tree = html.fromstring(response.content)
        self.assertFalse(tree.xpath('//form[contains(@action, "/calendar/cancel/")]'))
        response = self.url_open(f"/calendar/ics/{self.guest_token}.ics")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.event.booking_access_token, response.text)

    def test_cancellation_requires_post_and_csrf(self):
        token = self.event.booking_access_token
        response = self.url_open(f"/calendar/cancel/{token}", allow_redirects=False)
        self.assertEqual(response.status_code, 405)
        response = self.url_open(
            f"/calendar/cancel/{token}",
            data={"partner_id": self.customer.id},
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 400)
        self.event.invalidate_recordset(["active"])
        self.assertTrue(self.event.active)

    def test_all_day_google_export_uses_exclusive_end(self):
        for final_day in ("2035-03-15", "2035-03-17"):
            with self.subTest(final_day=final_day):
                self.event.write(
                    {
                        "allday": True,
                        "start_date": "2035-03-15",
                        "stop_date": final_day,
                    }
                )
                response = self.url_open(f"/calendar/view/{self.guest_token}")
                self.assertEqual(response.status_code, 200)
                tree = html.fromstring(response.content)
                link = tree.xpath('//a[contains(@class, "o_google_calendar")]/@href')[0]
                expected_end = (
                    datetime.fromisoformat(final_day) + timedelta(days=1)
                ).strftime("%Y%m%d")
                self.assertEqual(
                    parse_qs(urlsplit(link).query)["dates"],
                    [f"20350315/{expected_end}"],
                )

    def test_only_management_credentials_can_cancel_with_valid_csrf(self):
        response = self.url_open(f"/calendar/view/{self.event.booking_access_token}")
        tree = html.fromstring(response.content)
        csrf = tree.xpath('//input[@name="csrf_token"]/@value')[0]
        for token in (self.guest_token, self.event.access_token, "unknown-token"):
            with self.subTest(token=token):
                response = self.url_open(
                    f"/calendar/cancel/{token}",
                    data={"csrf_token": csrf, "partner_id": self.customer.id},
                    allow_redirects=False,
                )
                self.assertEqual(response.status_code, 404)
                self.event.invalidate_recordset(["active"])
                self.assertTrue(self.event.active)
        response = self.url_open(
            f"/calendar/cancel/{self.event.booking_access_token}",
            data={"csrf_token": csrf, "partner_id": self.guest.id},
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.event.invalidate_recordset(["active"])
        self.assertFalse(self.event.active)

    def test_ordinary_invitation_preserves_attendee_language(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.guest.lang = "fr_FR"
        self.event.appointment_type_id = False
        response = self.url_open(
            f"/calendar/meeting/view?token={self.guest_token}&id={self.event.id}"
        )
        self.assertEqual(response.status_code, 200)
        tree = html.fromstring(response.content)
        displayed_date = tree.xpath(
            '//div[contains(@class, "o_appointment_validation_details")]//strong'
        )[0].text_content()
        self.assertIn("mars", displayed_date)
