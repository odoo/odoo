from datetime import UTC, datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.libs.datetime import timezone
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestCalendarReservation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("calendar.block_mail", True)
        cls.organizer = new_test_user(
            cls.env, "resa_organizer", groups="base.group_user"
        )
        cls.invitee = new_test_user(cls.env, "resa_invitee", groups="base.group_user")
        cls.resources = cls.env["resource.resource"].create(
            [
                {"name": "Organizer", "user_id": cls.organizer.id},
                {"name": "Invitee", "user_id": cls.invitee.id},
            ]
        )
        cls.organizer_resource, cls.invitee_resource = cls.resources
        # A partner with no user at all: an external contact invited by e-mail.
        cls.external = cls.env["res.partner"].create({"name": "External Guest"})
        cls.start = datetime(2035, 3, 15, 10, 0)

    def _make_event(self, **kwargs):
        vals = {
            "name": "Design review",
            "start": self.start,
            "stop": self.start + timedelta(hours=2),
            "partner_ids": [
                (6, 0, [self.organizer.partner_id.id, self.invitee.partner_id.id])
            ],
        }
        vals.update(kwargs)
        return self.env["calendar.event"].with_user(self.organizer).create(vals)

    def _reservations(self, event):
        return (
            self.env["resource.reservation"]
            .sudo()
            .with_context(active_test=False)
            .search([("res_model", "=", "calendar.event"), ("res_id", "in", event.ids)])
        )

    # ------------------------------------------------------------------
    # Projection
    # ------------------------------------------------------------------

    def test_meeting_books_one_reservation_per_attendee_with_a_resource(self):
        event = self._make_event()
        reservations = self._reservations(event)
        self.assertEqual(
            reservations.resource_id,
            self.resources,
            "each attendee resolving to a resource books exactly one row",
        )
        self.assertEqual(set(reservations.mapped("date_start")), {self.start})
        self.assertEqual(
            set(reservations.mapped("date_end")), {self.start + timedelta(hours=2)}
        )
        self.assertEqual(set(reservations.mapped("allocated_percentage")), {100.0})

    def test_external_attendee_books_nothing(self):
        event = self._make_event(
            partner_ids=[(6, 0, [self.organizer.partner_id.id, self.external.id])]
        )
        self.assertEqual(
            self._reservations(event).resource_id,
            self.organizer_resource,
            "a contact with no user holds no capacity in this database",
        )

    def test_a_contractor_attendee_books_their_resource(self):
        contractor = self.env["res.partner"].create({"name": "Outside Welder"})
        (resource,) = contractor._get_or_create_resources(self.env.company)
        event = self._make_event(
            partner_ids=[(6, 0, [self.organizer.partner_id.id, contractor.id])]
        )
        self.assertFalse(contractor.user_ids, "the contractor has no login")
        self.assertIn(
            resource,
            self._reservations(event).resource_id,
            "a person is a resource through their party, login or not",
        )
        event.attendee_ids.filtered(
            lambda attendee: attendee.partner_id == contractor
        ).state = "declined"
        self.assertNotIn(resource, self._reservations(event).resource_id)

    def test_an_invitation_creates_no_resource(self):
        Resource = self.env["resource.resource"].with_context(active_test=False)
        before = Resource.search_count([])
        self._make_event(
            partner_ids=[(6, 0, [self.organizer.partner_id.id, self.external.id])]
        )
        self.assertEqual(
            Resource.search_count([]),
            before,
            "being invited to a meeting does not make a contact a resource",
        )

    def test_resource_ceiling_constrains_manual_meetings(self):
        self.organizer_resource.write(
            {"enforce_booking_limit": True, "booking_limit_percentage": 200}
        )
        first = self._make_event()
        self._make_event()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._make_event()
        first.show_as = "free"
        self._make_event()

    def test_busy_helpers_follow_all_day_resource_intervals(self):
        partner = self.organizer.partner_id
        for zone, day in (
            ("UTC", "2030-01-07"),
            ("Pacific/Kiritimati", "2030-01-07"),
            ("America/New_York", "2030-03-10"),
        ):
            with self.subTest(zone=zone):
                partner.tz = zone
                event = self._make_event(allday=True, start_date=day, stop_date=day)
                row = event.reservation_ids.filtered(
                    lambda row: row.resource_id == self.organizer_resource
                )
                for start in (row.date_start, row.date_end - timedelta(minutes=30)):
                    stop = start + timedelta(minutes=30)
                    self.assertIn(
                        event,
                        partner._get_busy_calendar_events(start, stop).get(
                            partner.id, self.env["calendar.event"]
                        ),
                    )
                self.assertNotIn(
                    event,
                    partner._get_busy_calendar_events(
                        row.date_end, row.date_end + timedelta(minutes=30)
                    ).get(partner.id, self.env["calendar.event"]),
                )
                event.unlink()

    def test_busy_helpers_ignore_declines_and_touching_intervals(self):
        event = self._make_event()
        partner = self.organizer.partner_id
        self.assertFalse(
            partner._get_busy_calendar_events(
                event.stop, event.stop + timedelta(hours=1)
            )
        )
        aware_start = event.start.replace(tzinfo=UTC).astimezone(timezone("Asia/Tokyo"))
        self.assertIn(
            event,
            partner._get_busy_calendar_events(
                aware_start, aware_start + timedelta(minutes=30)
            )[partner.id],
        )
        event.attendee_ids.filtered(
            lambda attendee: attendee.partner_id == partner
        ).do_decline()
        self.assertNotIn(
            partner.id, partner._get_busy_calendar_events(event.start, event.stop)
        )

    def test_all_day_guest_without_resource_uses_civil_dates(self):
        self.external.tz = "Pacific/Kiritimati"
        event = self._make_event(
            allday=True,
            start_date="2030-01-07",
            stop_date="2030-01-07",
            partner_ids=[(6, 0, self.external.ids)],
        )
        start = datetime(2030, 1, 6, 10)
        self.assertIn(
            event,
            self.external._get_busy_calendar_events(
                start, start + timedelta(minutes=30)
            )[self.external.id],
        )

    def test_event_shown_as_free_books_nothing(self):
        event = self._make_event(show_as="free")
        self.assertFalse(self._reservations(event))

    def test_all_day_conflict_indicator_uses_attendee_intervals(self):
        self.organizer.tz = "UTC"
        day = self._make_event(
            allday=True, start_date="2030-01-07", stop_date="2030-01-07"
        )
        early = self._make_event(
            start=datetime(2030, 1, 7, 7), stop=datetime(2030, 1, 7, 7, 30)
        )
        (day | early)._compute_unavailable_partner_ids()
        self.assertIn(self.organizer.partner_id, day.unavailable_partner_ids)
        self.assertIn(self.organizer.partner_id, early.unavailable_partner_ids)
        day.attendee_ids.filtered(
            lambda attendee: attendee.partner_id == self.organizer.partner_id
        ).do_decline()
        (day | early)._compute_unavailable_partner_ids()
        self.assertNotIn(self.organizer.partner_id, day.unavailable_partner_ids)
        self.assertNotIn(self.organizer.partner_id, early.unavailable_partner_ids)

    def test_flipping_show_as_releases_and_retakes_the_claims(self):
        event = self._make_event()
        self.assertEqual(len(self._reservations(event)), 2)
        event.show_as = "free"
        self.assertFalse(
            self._reservations(event), "marking the time free must release it"
        )
        event.show_as = "busy"
        self.assertEqual(
            len(self._reservations(event)), 2, "and marking it busy must retake it"
        )

    def test_moving_the_meeting_moves_the_bookings(self):
        event = self._make_event()
        event.write(
            {
                "start": self.start + timedelta(days=1),
                "stop": self.start + timedelta(days=1, hours=2),
            }
        )
        self.assertEqual(
            set(self._reservations(event).mapped("date_start")),
            {self.start + timedelta(days=1)},
        )

    def test_renaming_the_meeting_relabels_the_bookings(self):
        event = self._make_event()
        event.name = "Renamed review"
        self.assertEqual(
            set(self._reservations(event).mapped("name")), {"Renamed review"}
        )

    def test_removing_an_attendee_releases_their_booking(self):
        event = self._make_event()
        event.partner_ids = [(6, 0, [self.organizer.partner_id.id])]
        self.assertEqual(self._reservations(event).resource_id, self.organizer_resource)

    # ------------------------------------------------------------------
    # Conflicts — the point of the whole exercise
    # ------------------------------------------------------------------

    def test_two_meetings_on_the_same_person_conflict(self):
        first = self._make_event()
        second = self._make_event(
            name="Clashing meeting",
            start=self.start + timedelta(hours=1),
            stop=self.start + timedelta(hours=3),
        )
        self.assertTrue(
            first.schedule_overlap_count,
            "an overlapping meeting must be visible as a conflict",
        )
        self.assertTrue(second.schedule_overlap_count)

    def test_a_meeting_conflicts_with_a_foreign_ledger_claim(self):
        """The ledger is model-agnostic: a shift booked by another consumer
        (planning, mrp, project) clashes with a meeting just the same. Stand in
        for that consumer with a raw claim, since none of them is installable
        from `calendar`'s own dependency set."""
        self.env["resource.reservation"].sudo().create(
            {
                "name": "Warehouse shift",
                "date_start": self.start + timedelta(hours=1),
                "date_end": self.start + timedelta(hours=4),
                "resource_id": self.invitee_resource.id,
                "res_model": "planning.slot",
                "res_id": 1,
                "enforcement_mode": "soft",
            }
        )
        event = self._make_event()
        self.assertTrue(
            event.schedule_overlap_count,
            "a meeting must collide with a shift on the same resource",
        )

    def test_non_overlapping_meetings_do_not_conflict(self):
        first = self._make_event()
        second = self._make_event(
            name="Later meeting",
            start=self.start + timedelta(hours=3),
            stop=self.start + timedelta(hours=4),
        )
        self.assertFalse(first.schedule_overlap_count)
        self.assertFalse(second.schedule_overlap_count)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def test_archiving_releases_the_claims_and_restoring_retakes_them(self):
        event = self._make_event()
        event.action_archive()
        self.assertFalse(
            self._reservations(event).filtered("active"),
            "an archived meeting is not a live claim on anyone",
        )
        event.action_unarchive()
        self.assertEqual(len(self._reservations(event).filtered("active")), 2)

    def test_deleting_the_meeting_leaves_no_orphan_rows(self):
        event = self._make_event()
        event_id = event.id
        event.unlink()
        self.assertFalse(
            self.env["resource.reservation"]
            .sudo()
            .with_context(active_test=False)
            .search([("res_model", "=", "calendar.event"), ("res_id", "=", event_id)])
        )

    # ------------------------------------------------------------------
    # Recurrence — the reason the sync is manual
    # ------------------------------------------------------------------

    def test_a_recurrence_books_every_occurrence_exactly_once(self):
        event = self._make_event(
            recurrency=True,
            repeat_unit="day",
            repeat_interval=1,
            repeat_type="count",
            repeat_number=3,
        )
        occurrences = event.recurrence_id.calendar_event_ids
        self.assertEqual(len(occurrences), 3)
        reservations = self._reservations(occurrences)
        self.assertEqual(
            len(reservations), 6, "3 occurrences x 2 attendees, no duplicates"
        )

    def test_rewriting_a_whole_recurrence_leaves_one_booking_set_per_occurrence(self):
        """`_rewrite_recurrence` never calls `super().write()` on `self`, so an
        automatic sync hook would not fire here at all."""
        event = self._make_event(
            recurrency=True,
            repeat_unit="day",
            repeat_interval=1,
            repeat_type="count",
            repeat_number=3,
        )
        base = event.recurrence_id.base_event_id
        base.write(
            {
                "recurrence_update": "all",
                "start": self.start + timedelta(hours=4),
                "stop": self.start + timedelta(hours=6),
            }
        )
        occurrences = base.recurrence_id.calendar_event_ids
        live = self._reservations(occurrences).filtered("active")
        self.assertEqual(
            len(live),
            2 * len(occurrences),
            "every occurrence keeps exactly one booking per attendee",
        )
        self.assertEqual(
            {r.date_start.hour for r in live},
            {14},
            "the rewritten times must reach the ledger",
        )

    def test_declining_releases_and_accepting_rebooks(self):
        event = self._make_event()
        attendee = event.attendee_ids.filtered(
            lambda a: a.partner_id == self.invitee.partner_id
        )
        attendee.write({"state": "declined"})
        self.assertEqual(self._reservations(event).resource_id, self.organizer_resource)
        attendee.write({"state": "accepted"})
        self.assertEqual(self._reservations(event).resource_id, self.resources)

    def test_all_day_uses_local_midnights_across_dst(self):
        self.invitee.tz = "America/New_York"
        event = self._make_event(
            allday=True,
            start_date="2030-03-10",
            stop_date="2030-03-10",
            partner_ids=[(6, 0, self.invitee.partner_id.ids)],
        )
        reservation = self._reservations(event)
        self.assertEqual(reservation.date_start, datetime(2030, 3, 10, 5))
        self.assertEqual(reservation.date_end, datetime(2030, 3, 11, 4))

    def test_first_enforced_booking_recovers_existing_meeting_occupancy(self):
        user = new_test_user(
            self.env, "booking_without_resource", groups="base.group_user"
        )
        event = self._make_event(partner_ids=[(6, 0, user.partner_id.ids)])
        self.assertFalse(self._reservations(event))
        resource = user._get_or_create_calendar_event_resource()
        self.assertEqual(self._reservations(event).resource_id, resource)
        self.assertEqual(user._get_or_create_calendar_event_resource(), resource)

    def test_clearing_then_restoring_attendees_has_no_duplicates(self):
        event = self._make_event()
        partners = event.partner_ids
        event.partner_ids = False
        self.assertFalse(event.attendee_ids)
        self.assertFalse(self._reservations(event))
        event.partner_ids = partners
        self.assertEqual(len(event.attendee_ids), len(partners))
        self.assertEqual(self._reservations(event).resource_id, self.resources)
