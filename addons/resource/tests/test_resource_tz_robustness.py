from datetime import UTC, datetime

from odoo.libs.datetime import timezone
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestLeaveDateToMultiCompanyTz(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env["res.company"].create({"name": "TZ Co A"})
        cls.company_b = cls.env["res.company"].create({"name": "TZ Co B"})
        cls.company_a.resource_calendar_id.tz = "Europe/Brussels"
        cls.company_b.resource_calendar_id.tz = "Asia/Tokyo"

    def _tzless_leaves_model(self):
        root = self.env.ref("base.user_root")
        root.tz = False
        return (
            self.env["resource.schedule.exception"]
            .sudo()
            .with_context(
                tz=None,
                allowed_company_ids=[self.company_a.id, self.company_b.id],
            )
        )

    def test_multi_company_batch_create_does_not_raise(self):
        leaves = self._tzless_leaves_model().create(
            [
                {
                    "name": "A",
                    "calendar_id": self.company_a.resource_calendar_id.id,
                    "date_from": datetime(2025, 1, 6, 8, 0),
                },
                {
                    "name": "B",
                    "calendar_id": self.company_b.resource_calendar_id.id,
                    "date_from": datetime(2025, 1, 6, 8, 0),
                },
            ]
        )
        self.assertEqual(len(leaves), 2)
        self.assertTrue(all(leaves.mapped("date_to")))

    def test_date_to_uses_each_leaves_own_calendar_tz(self):
        leaves = self._tzless_leaves_model().create(
            [
                {
                    "name": "A",
                    "calendar_id": self.company_a.resource_calendar_id.id,
                    "date_from": datetime(2025, 1, 6, 8, 0),
                },
                {
                    "name": "B",
                    "calendar_id": self.company_b.resource_calendar_id.id,
                    "date_from": datetime(2025, 1, 6, 8, 0),
                },
            ]
        )
        leave_a, leave_b = leaves[0], leaves[1]
        self.assertEqual(leave_a.date_to, datetime(2025, 1, 6, 22, 59, 59))
        self.assertEqual(leave_b.date_to, datetime(2025, 1, 6, 14, 59, 59))

    def test_date_to_calendar_tz_wins_over_the_acting_users_tz(self):
        # Company A's calendar is Europe/Brussels (UTC+1 in January); the
        # acting user is in Asia/Tokyo (UTC+9). Both compute() and
        # default_get() must resolve the same "end of day": the calendar's.
        leave = (
            self.env["resource.schedule.exception"]
            .with_context(tz="Asia/Tokyo")
            .create(
                {
                    "name": "A",
                    "calendar_id": self.company_a.resource_calendar_id.id,
                    "date_from": datetime(2025, 1, 6, 8, 0),
                }
            )
        )
        self.assertEqual(leave.date_to, datetime(2025, 1, 6, 22, 59, 59))


@tagged("post_install", "-at_install")
class TestIntervalBatchStringTz(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "String TZ", "tz": "UTC"}
        )
        cls.resource = cls.env["resource.resource"].create(
            {"name": "STZ res", "calendar_id": cls.calendar.id, "tz": "UTC"}
        )
        cls.env["resource.schedule.exception"].create(
            {
                "name": "Global off",
                "calendar_id": cls.calendar.id,
                "date_from": datetime(2025, 1, 8, 0, 0),
                "date_to": datetime(2025, 1, 8, 23, 59),
            }
        )
        cls.start = datetime(2025, 1, 6, 0, 0).replace(tzinfo=UTC)
        cls.end = datetime(2025, 1, 11, 0, 0).replace(tzinfo=UTC)
        cls.tz_str = "Europe/Brussels"
        cls.tz_obj = timezone("Europe/Brussels")

    def test_attendance_intervals_string_tz(self):
        by_str = self.calendar._attendance_intervals_batch(
            self.start, self.end, self.resource, tz=self.tz_str
        )
        by_obj = self.calendar._attendance_intervals_batch(
            self.start, self.end, self.resource, tz=self.tz_obj
        )
        self.assertEqual(list(by_str[self.resource.id]), list(by_obj[self.resource.id]))

    def test_leave_intervals_string_tz(self):
        by_str = self.calendar._leave_intervals_batch(
            self.start, self.end, self.resource, tz=self.tz_str
        )
        by_obj = self.calendar._leave_intervals_batch(
            self.start, self.end, self.resource, tz=self.tz_obj
        )
        self.assertEqual(list(by_str[self.resource.id]), list(by_obj[self.resource.id]))

    def test_work_intervals_string_tz(self):
        by_str = self.calendar._work_intervals_batch(
            self.start, self.end, self.resource, tz=self.tz_str
        )
        by_obj = self.calendar._work_intervals_batch(
            self.start, self.end, self.resource, tz=self.tz_obj
        )
        self.assertEqual(list(by_str[self.resource.id]), list(by_obj[self.resource.id]))

    def test_unavailable_intervals_string_tz(self):
        by_str = self.calendar._unavailable_intervals_batch(
            self.start, self.end, self.resource, tz=self.tz_str
        )
        by_obj = self.calendar._unavailable_intervals_batch(
            self.start, self.end, self.resource, tz=self.tz_obj
        )
        self.assertEqual(by_str[self.resource.id], by_obj[self.resource.id])
