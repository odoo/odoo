from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from odoo.exceptions import ValidationError
from odoo.libs.intervals import Intervals
from odoo.tests import TransactionCase, tagged

from odoo.addons.resource.models.utils import peak_capacity


@tagged("post_install", "-at_install")
class TestBookingCapacity(TransactionCase):
    def setUp(self):
        super().setUp()
        self.resource = self.env["resource.resource"].create(
            {
                "name": "Constrained overbooking",
                "booking_limit_percentage": 125,
            }
        )
        self.start = datetime(2030, 1, 7, 10)
        self.stop = self.start + timedelta(hours=1)

    def book(self, percentage, **values):
        return self.env["resource.reservation"].create(
            {
                "name": "Capacity test",
                "resource_id": self.resource.id,
                "date_start": self.start,
                "date_end": self.stop,
                "allocated_percentage": percentage,
                "enforcement_mode": "hard",
                **values,
            }
        )

    def test_flexible_week_bounds_follow_local_calendar(self):
        for zone, start, stop, expected_start, expected_stop in [
            (
                "Pacific/Auckland",
                datetime(2025, 7, 27, 22, tzinfo=UTC),
                datetime(2025, 7, 27, 23, tzinfo=UTC),
                datetime(2025, 7, 27, 12, tzinfo=UTC),
                datetime(2025, 8, 3, 12, tzinfo=UTC),
            ),
            (
                "America/New_York",
                datetime(2025, 3, 9, 6, tzinfo=UTC),
                datetime(2025, 3, 9, 8, tzinfo=UTC),
                datetime(2025, 3, 3, 5, tzinfo=UTC),
                datetime(2025, 3, 10, 4, tzinfo=UTC),
            ),
        ]:
            with self.subTest(zone=zone):
                self.resource.tz = zone
                self.assertEqual(
                    self.resource._get_flexible_week_bounds(start, stop),
                    (expected_start, expected_stop),
                )

    def test_flexible_booking_effort_uses_local_dates_and_elapsed_hours(self):
        self.resource.calendar_id = self.env["resource.calendar"].create(
            {
                "name": "Timezone effort",
                "flexible_hours": True,
                "hours_per_day": 8,
                "full_time_required_hours": 40,
            }
        )
        cases = [
            (
                "Pacific/Auckland",
                datetime(2025, 7, 27, 22, tzinfo=UTC),
                datetime(2025, 7, 27, 23, tzinfo=UTC),
                date(2025, 7, 28),
                1,
            ),
            (
                "America/New_York",
                datetime(2025, 3, 9, 1, tzinfo=ZoneInfo("America/New_York")),
                datetime(2025, 3, 9, 4, tzinfo=ZoneInfo("America/New_York")),
                date(2025, 3, 9),
                2,
            ),
        ]
        for zone, start, stop, day, expected in cases:
            with self.subTest(zone=zone):
                self.resource.tz = zone
                begin, end = self.resource._get_flexible_week_bounds(start, stop)
                hours = self.resource._get_flexible_booking_hours_per_day(
                    {self.resource.id: [(start, stop, 100)]}, begin, end
                )
                self.assertEqual(dict(hours[self.resource.id]), {day: expected})
        self.resource.calendar_id = False
        self.assertEqual(
            self.resource._get_flexible_resource_work_hours(
                Intervals([(cases[-1][1], cases[-1][2], set())]), {}, {}
            ),
            2,
        )

    def test_flexible_work_outside_provided_budget_is_zero(self):
        self.resource.calendar_id = self.env["resource.calendar"].create(
            {
                "name": "Bounded effort",
                "flexible_hours": True,
                "hours_per_day": 8,
            }
        )
        self.resource.tz = "UTC"
        hours = self.resource._get_flexible_resource_work_hours(
            Intervals(
                [
                    (
                        datetime(2025, 7, 27, 10, tzinfo=UTC),
                        datetime(2025, 7, 27, 11, tzinfo=UTC),
                        set(),
                    )
                ]
            ),
            {date(2025, 7, 28): 8},
            {(2025, 31): 40},
        )
        self.assertEqual(hours, 0)

    def test_flexible_booking_effort_is_weighted_clipped_and_leave_aware(self):
        self.resource.write(
            {
                "tz": "UTC",
                "calendar_id": self.env["resource.calendar"]
                .create(
                    {
                        "name": "Flexible booking effort",
                        "tz": "UTC",
                        "flexible_hours": True,
                        "hours_per_day": 8,
                        "full_time_required_hours": 40,
                    }
                )
                .id,
            }
        )
        bookings = {
            self.resource.id: [
                (datetime(2025, 7, 28, 8), datetime(2025, 7, 28, 12), 50),
                (datetime(2025, 7, 28, 12), datetime(2025, 7, 28, 16), 25),
                (datetime(2025, 7, 29), datetime(2025, 7, 30), 100),
            ]
        }
        start, stop = (
            datetime(2025, 7, 28, 10, tzinfo=UTC),
            datetime(2025, 7, 29, 12, tzinfo=UTC),
        )
        hours = self.resource._get_flexible_booking_hours_per_day(
            bookings, start, stop
        )[self.resource.id]
        self.assertAlmostEqual(hours[date(2025, 7, 28)], 2)
        self.assertAlmostEqual(hours[date(2025, 7, 29)], 8)
        self.env["resource.schedule.exception"].create(
            {
                "name": "Unavailable day",
                "resource_id": self.resource.id,
                "calendar_id": self.resource.calendar_id.id,
                "date_from": datetime(2025, 7, 28),
                "date_to": datetime(2025, 7, 29),
            }
        )
        hours = self.resource._get_flexible_booking_hours_per_day(
            bookings, start, stop
        )[self.resource.id]
        self.assertAlmostEqual(hours[date(2025, 7, 28)], 0)
        self.assertAlmostEqual(hours[date(2025, 7, 29)], 8)

    def test_under_full_over_and_exceeded(self):
        first = self.book(75)
        self.assertEqual(first.booking_state, "under")
        self.book(25)
        first._compute_booking_load()
        self.assertEqual(first.booking_state, "full")
        self.book(25)
        first._compute_booking_load()
        self.assertEqual(first.booking_state, "over")
        self.assertEqual(first.peak_booking_percentage, 125)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.book(0.01)

    def test_single_overbooking_is_bounded_without_a_peer(self):
        booking = self.book(125)
        self.assertEqual(booking.booking_state, "over")
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            booking.allocated_percentage = 126

    def test_lowering_ceiling_checks_existing_enforced_bookings(self):
        self.book(125)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.resource.booking_limit_percentage = 100

    def test_adjacent_bookings_do_not_accumulate(self):
        self.book(100)
        self.book(100, date_start=self.stop, date_end=self.stop + timedelta(hours=1))
        booking = self.book(25, date_end=self.stop + timedelta(hours=1))
        self.assertEqual(booking.peak_booking_percentage, 125)

    def test_zero_does_not_consume_capacity(self):
        self.resource.booking_limit_percentage = 0
        self.assertEqual(self.book(0).peak_booking_percentage, 0)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.book(1)

    def test_warning_only_excess_is_explicit(self):
        booking = self.book(150, enforcement_mode="soft")
        self.assertEqual(booking.booking_state, "exceeded")
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            booking.enforcement_mode = "hard"

    def test_sweep_clips_and_handles_equal_boundaries(self):
        self.assertEqual(
            peak_capacity(
                [
                    (self.start - timedelta(hours=1), self.start, 1000),
                    (self.start, self.stop, 40),
                    (self.stop, self.stop + timedelta(hours=1), 60),
                    (self.start, self.stop + timedelta(hours=1), 25),
                ],
                self.start,
                self.stop + timedelta(hours=1),
            ),
            85,
        )

    def test_enforced_booking_does_not_subtract_its_own_effort(self):
        booking = self.book(125)
        self.assertAlmostEqual(booking.allocated_hours, 1.25)

    def test_resource_policy_constrains_warning_bookings(self):
        self.resource.enforce_booking_limit = True
        first = self.book(75, enforcement_mode="soft")
        self.book(50, enforcement_mode="soft")
        self.assertEqual(first.booking_state, "over")
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.book(1, enforcement_mode="soft")

    def test_enabling_policy_validates_existing_load(self):
        self.book(150, enforcement_mode="soft")
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.resource.enforce_booking_limit = True
        self.resource.write(
            {"booking_limit_percentage": 150, "enforce_booking_limit": True}
        )
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.resource.booking_limit_percentage = 125

    def test_resource_policy_checks_moves_and_reactivation(self):
        self.resource.enforce_booking_limit = True
        self.book(125, enforcement_mode="soft")
        archived = self.book(25, enforcement_mode="soft", active=False)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            archived.active = True
        other = self.resource.copy({"enforce_booking_limit": False})
        moved = self.book(25, resource_id=other.id, enforcement_mode="soft")
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            moved.resource_id = self.resource

    def test_disabling_resource_policy_keeps_individual_enforcement(self):
        self.resource.enforce_booking_limit = True
        self.book(125)
        self.resource.enforce_booking_limit = False
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.book(1, enforcement_mode="soft")
