from datetime import datetime, timedelta

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResourceAssetCalendar(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, no_mail_to_attendees=True))
        cls.kind = cls.env.ref("resource_asset.kind_equipment")
        cls.projector = cls.env["resource.asset"].create(
            {"name": "Projector", "kind_id": cls.kind.id, "state": "in_service"}
        )
        cls.start = datetime(2026, 10, 5, 9, 0)

    def _book(self, profile, start=None, hours=1):
        start = start or self.start
        offer = self.env["appointment.type"].create(
            {
                "name": "Equipment booking",
                "schedule_based_on": "resources",
                "resource_ids": [Command.set(profile.ids)],
            }
        )
        return self.env["calendar.event"].create(
            {
                "name": "Presentation",
                "start": start,
                "stop": start + timedelta(hours=hours),
                "appointment_type_id": offer.id,
                "booking_line_ids": [
                    Command.create(
                        {"appointment_resource_id": profile.id, "capacity_reserved": 1}
                    )
                ],
            }
        )

    def test_a_profile_created_on_an_asset_shares_its_resource_and_name(self):
        profile = self.env["appointment.resource"].create(
            {"asset_id": self.projector.id, "name": "Something else"}
        )
        self.assertEqual(profile.resource_id, self.projector.resource_id)
        self.assertEqual(self.projector.appointment_resource_id, profile)
        self.assertEqual(profile.name, "Projector")
        self.assertEqual(self.projector.name, "Projector")

    def test_attaching_later_swaps_the_resource_and_detaching_gives_one_back(self):
        profile = self.env["appointment.resource"].create({"name": "Loose projector"})
        own = profile.resource_id
        profile.asset_id = self.projector
        self.assertEqual(profile.resource_id, self.projector.resource_id)
        self.assertFalse(own.active)
        profile.asset_id = False
        self.assertNotEqual(profile.resource_id, self.projector.resource_id)
        self.assertTrue(profile.resource_id.active)
        self.assertTrue(self.projector.resource_id.active)

    def test_one_profile_per_asset_even_within_one_create(self):
        with self.assertRaises(ValidationError):
            self.env["appointment.resource"].create(
                [{"asset_id": self.projector.id}, {"asset_id": self.projector.id}]
            )
        self.env["appointment.resource"].create({"asset_id": self.projector.id})
        with self.assertRaises(ValidationError):
            self.env["appointment.resource"].create({"asset_id": self.projector.id})

    def test_an_existing_profile_is_attached_from_the_asset(self):
        profile = self.env["appointment.resource"].create({"name": "Loose projector"})
        own = profile.resource_id
        self.projector.appointment_resource_id = profile
        self.assertEqual(profile.asset_id, self.projector)
        self.assertEqual(profile.resource_id, self.projector.resource_id)
        self.assertFalse(own.active)

    def test_assets_are_found_by_their_booking_profile(self):
        profile = self.projector._create_appointment_resources()
        Asset = self.env["resource.asset"]
        self.assertEqual(
            Asset.search([("appointment_resource_id", "in", profile.ids)]),
            self.projector,
        )
        self.assertIn(
            self.projector,
            Asset.search([("appointment_resource_id", "!=", False)]),
        )
        self.assertNotIn(
            self.projector,
            Asset.search([("appointment_resource_id", "=", False)]),
        )

    def test_make_bookable_creates_the_profile_once(self):
        first = self.projector._create_appointment_resources()
        second = self.projector._create_appointment_resources()
        self.assertEqual(self.projector.appointment_resource_id, first)
        self.assertFalse(second)

    def test_an_asset_out_of_service_refuses_a_booking(self):
        profile = self.projector._create_appointment_resources()
        self.assertTrue(self._book(profile).reservation_ids)
        for state in ("draft", "out_of_service"):
            self.projector.state = state
            with self.assertRaises(ValidationError):
                self._book(profile, start=self.start + timedelta(days=1))
        self.projector.action_dispose()
        with self.assertRaises(ValidationError):
            self._book(profile, start=self.start + timedelta(days=2))

    def test_an_asset_under_maintenance_is_still_offered(self):
        profile = self.projector._create_appointment_resources()
        self.projector.state = "maintenance"
        self.assertTrue(self._book(profile).reservation_ids)

    def test_slot_search_skips_an_asset_that_is_not_bookable(self):
        profile = self.projector._create_appointment_resources()
        offer = self.env["appointment.type"].create(
            {
                "name": "Equipment booking",
                "schedule_based_on": "resources",
                "resource_ids": [Command.set(profile.ids)],
            }
        )
        slot = {
            "slot": self.env["appointment.slot"],
            "UTC": (self.start, self.start + timedelta(hours=1)),
        }
        values = {"resource_to_bookings": {}}
        self.assertTrue(
            offer._slot_availability_is_resource_available(slot, profile, values)
        )
        self.projector.state = "out_of_service"
        self.assertFalse(
            offer._slot_availability_is_resource_available(slot, profile, values)
        )

    def test_a_hard_reservation_on_the_asset_refuses_an_overlapping_booking(self):
        profile = self.projector._create_appointment_resources()
        self.projector.resource_id.enforce_booking_limit = True
        self.env["resource.reservation"].create(
            {
                "name": "Lamp replacement",
                "resource_id": self.projector.resource_id.id,
                "date_start": self.start,
                "date_end": self.start + timedelta(hours=2),
                "enforcement_mode": "hard",
            }
        )
        self.assertTrue(
            self._book(profile, start=self.start + timedelta(hours=2)).reservation_ids
        )
        with self.assertRaises(ValidationError):
            self._book(profile, start=self.start + timedelta(minutes=30))
