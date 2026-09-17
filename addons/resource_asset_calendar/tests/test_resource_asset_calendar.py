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

    def _offer(self, asset):
        return self.env["appointment.type"].create(
            {
                "name": "Equipment booking",
                "schedule_based_on": "resources",
                "resource_ids": [Command.set(asset.resource_id.ids)],
            }
        )

    def _book(self, asset, start=None, hours=1):
        start = start or self.start
        offer = self._offer(asset)
        return self.env["calendar.event"].create(
            {
                "name": "Presentation",
                "start": start,
                "stop": start + timedelta(hours=hours),
                "appointment_type_id": offer.id,
                "booking_line_ids": [
                    Command.create(
                        {
                            "resource_id": asset.resource_id.id,
                            "capacity_reserved": 1,
                        }
                    )
                ],
            }
        )

    def test_an_offer_made_on_the_asset_reaches_its_resource(self):
        offer = self._offer(self.projector)
        self.assertEqual(self.projector.appointment_type_ids, offer)
        self.assertTrue(self.projector.is_bookable)
        self.assertTrue(self.projector.resource_id.is_bookable)

    def test_the_asset_offers_itself(self):
        offer = self.env["appointment.type"].create(
            {"name": "Equipment booking", "schedule_based_on": "resources"}
        )
        self.projector.appointment_type_ids = offer
        self.assertEqual(offer.resource_ids, self.projector.resource_id)

    def test_assets_are_found_by_what_offers_them(self):
        offer = self._offer(self.projector)
        Asset = self.env["resource.asset"]
        self.assertEqual(
            Asset.search([("appointment_type_ids", "in", offer.ids)]), self.projector
        )
        self.assertIn(self.projector, Asset.search([("is_bookable", "=", True)]))

    def test_an_asset_out_of_service_refuses_a_booking(self):
        self.assertTrue(self._book(self.projector).reservation_ids)
        for state in ("draft", "out_of_service"):
            self.projector.state = state
            with self.assertRaises(ValidationError):
                self._book(self.projector, start=self.start + timedelta(days=1))
        self.projector.action_dispose()
        with self.assertRaises(ValidationError):
            self._book(self.projector, start=self.start + timedelta(days=2))

    def test_an_asset_under_maintenance_is_still_offered(self):
        self.projector.state = "maintenance"
        self.assertTrue(self._book(self.projector).reservation_ids)

    def test_slot_search_skips_an_asset_that_is_not_bookable(self):
        offer = self._offer(self.projector)
        slot = {
            "slot": self.env["appointment.slot"],
            "UTC": (self.start, self.start + timedelta(hours=1)),
        }
        values = {"resource_to_bookings": {}}
        self.assertTrue(
            offer._slot_availability_is_resource_available(
                slot, self.projector.resource_id, values
            )
        )
        self.projector.state = "out_of_service"
        self.assertFalse(
            offer._slot_availability_is_resource_available(
                slot, self.projector.resource_id, values
            )
        )

    def test_a_hard_reservation_on_the_asset_refuses_an_overlapping_booking(self):
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
            self._book(
                self.projector, start=self.start + timedelta(hours=2)
            ).reservation_ids
        )
        with self.assertRaises(ValidationError):
            self._book(self.projector, start=self.start + timedelta(minutes=30))
