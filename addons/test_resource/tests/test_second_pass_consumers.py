"""Second-pass regressions that need a real ``mixin.resource`` /
``mixin.resource.scheduling`` consumer, which is why they live here rather than
in ``resource`` itself: that module's tests run before this one is in the
registry.
"""

from datetime import UTC, datetime

from psycopg.errors import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestResourceSecondPassConsumers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Second Pass Co"})
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "SP calendar", "company_id": cls.company.id, "tz": "UTC"}
        )

    def _resource(self, **vals):
        return self.env["resource.resource"].create(
            {
                "name": vals.pop("name", "SP resource"),
                "company_id": vals.pop("company_id", self.company.id),
                "calendar_id": vals.pop("calendar_id", self.calendar.id),
                "tz": vals.pop("tz", "UTC"),
                **vals,
            }
        )

    def test_consumer_can_filter_its_conflicted_records(self):
        resource = self._resource(name="Consumer conflict")
        model = self.env["resource.scheduling.test"]
        vals = {
            "company_id": self.company.id,
            "resource_id": resource.id,
            "date_start": datetime(2026, 3, 4, 8, 0),
            "date_end": datetime(2026, 3, 4, 12, 0),
        }
        first = model.create({"name": "one", **vals})
        second = model.create({"name": "two", **vals})
        conflicted = model.search([("schedule_overlap_count", "!=", 0)])
        self.assertLessEqual({first.id, second.id}, set(conflicted.ids))

    def test_attaching_to_a_resource_keeps_its_company_and_calendar(self):
        """A consumer must not repoint the resource it attaches to.

        ``company_id`` and ``resource_calendar_id`` are stored, writable
        *related* fields, so the defaults they used to carry were written
        straight through onto the resource at create time -- handing a
        company-A resource the acting company's schedule, silently.
        """
        resource = self._resource(name="Keeps its calendar")
        record = self.env["resource.test"].create(
            {"name": "attached", "resource_id": resource.id}
        )
        self.assertEqual(resource.calendar_id, self.calendar)
        self.assertEqual(resource.company_id, self.company)
        self.assertEqual(record.resource_calendar_id, self.calendar)
        self.assertEqual(record.company_id, self.company)

    def test_fully_flexible_leave_days_count_inclusively(self):
        """One whole day is one day, not zero."""
        record = self.env["resource.test"].create({"name": "flex"})
        record.resource_id.calendar_id = False
        self.env.flush_all()
        one_day = record._get_leave_days_data_batch(
            datetime(2026, 3, 2, 0, 0).replace(tzinfo=UTC),
            datetime(2026, 3, 2, 23, 59, 59).replace(tzinfo=UTC),
        )
        self.assertEqual(one_day[record.id]["days"], 1)
        five_days = record._get_leave_days_data_batch(
            datetime(2026, 3, 2, 0, 0).replace(tzinfo=UTC),
            datetime(2026, 3, 6, 23, 59, 59).replace(tzinfo=UTC),
        )
        self.assertEqual(five_days[record.id]["days"], 5)

    def test_a_resource_has_one_owner_and_a_batch_answers_each(self):
        # a resource has one owner (mixin.resource.resource_id is unique):
        # two records of one model cannot share it, and a batch over records
        # of distinct resources answers every one of them
        one = self._resource(name="One")
        first = self.env["resource.test"].create(
            {"name": "first", "resource_id": one.id, "company_id": self.company.id}
        )
        with self.assertRaises(IntegrityError), mute_logger("odoo.db.cursor"):
            with self.env.cr.savepoint():
                self.env["resource.test"].create(
                    {
                        "name": "second",
                        "resource_id": one.id,
                        "company_id": self.company.id,
                    }
                )
        second = self.env["resource.test"].create(
            {
                "name": "second",
                "resource_id": self._resource(name="Other").id,
                "company_id": self.company.id,
            }
        )
        window = (
            datetime(2026, 3, 2).replace(tzinfo=UTC),
            datetime(2026, 3, 7).replace(tzinfo=UTC),
        )
        work = (first | second)._get_work_days_data_batch(*window)
        leave = (first | second)._get_leave_days_data_batch(*window)
        for result in (work, leave):
            self.assertEqual(set(result), {first.id, second.id})
            self.assertEqual(result[first.id], result[second.id])

    def test_orphan_reservations_are_garbage_collected(self):
        resource = self._resource(name="Orphan maker")
        record = self.env["resource.scheduling.test"].create(
            {
                "name": "will be deleted behind the ORM's back",
                "company_id": self.company.id,
                "resource_id": resource.id,
                "date_start": datetime(2026, 3, 2, 8, 0),
                "date_end": datetime(2026, 3, 2, 17, 0),
            }
        )
        self.env.flush_all()
        record_id = record.id
        self.env.cr.execute(
            "DELETE FROM resource_scheduling_test WHERE id = %s", (record_id,)
        )
        self.env.invalidate_all()

        reservations = self.env["resource.reservation"].search(
            [("res_model", "=", "resource.scheduling.test"), ("res_id", "=", record_id)]
        )
        self.assertTrue(reservations, "precondition: the orphan survives the delete")

        self.env["resource.reservation"]._gc_orphan_reservations()
        self.assertFalse(reservations.exists())

    def test_gc_keeps_live_and_standalone_reservations(self):
        resource = self._resource(name="Keep me")
        live = self.env["resource.scheduling.test"].create(
            {
                "name": "alive",
                "company_id": self.company.id,
                "resource_id": resource.id,
                "date_start": datetime(2026, 3, 2, 8, 0),
                "date_end": datetime(2026, 3, 2, 17, 0),
            }
        )
        standalone = self.env["resource.reservation"].create(
            {
                "name": "no origin",
                "resource_id": resource.id,
                "date_start": datetime(2026, 3, 9, 8, 0),
                "date_end": datetime(2026, 3, 9, 17, 0),
            }
        )
        self.env.flush_all()
        mirrored = live.reservation_ids
        self.assertTrue(mirrored)

        self.env["resource.reservation"]._gc_orphan_reservations()
        self.assertTrue(mirrored.exists(), "a live consumer keeps its reservations")
        self.assertTrue(
            standalone.exists(), "a booking with no origin is not an orphan"
        )
