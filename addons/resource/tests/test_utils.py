from datetime import UTC, date, datetime

from dateutil.relativedelta import relativedelta

from odoo.fields import Datetime, Domain
from odoo.libs.datetime import timezone
from odoo.tests import Form
from odoo.tests.common import TransactionCase

from odoo.addons.resource.models import utils


class TestExpression(TransactionCase):
    def test_filter_domain_leaf(self):
        domains = [
            ["|", ("skills", "=", 1), ("admin", "=", True)],
            [
                "|",
                ("skills", "=", 1),
                ("admin", "=", True),
                "|",
                ("skills", "=", 2),
                ("admin", "=", True),
            ],
            [
                "|",
                ("skills", "=", 1),
                ("skills", "=", 2),
                "|",
                ("skills", "=", 2),
                ("admin", "=", True),
            ],
            [
                "|",
                "|",
                ("skills", "=", 1),
                ("skills", "=", True),
                "|",
                ("skills", "=", 2),
                ("admin", "=", True),
            ],
            [
                "|",
                "|",
                ("admin", "=", 1),
                ("admin", "=", True),
                "&",
                ("skills", "=", 2),
                ("admin", "=", True),
            ],
            [
                "|",
                "|",
                "!",
                ("admin", "=", 1),
                ("admin", "=", True),
                "!",
                "&",
                "!",
                ("skills", "=", 2),
                ("admin", "=", True),
            ],
            ["&", "!", ("skills", "=", 2), ("admin", "=", True)],
            [
                ["start_datetime", "<=", "2022-12-17 22:59:59"],
                ["end_datetime", ">=", "2022-12-10 23:00:00"],
            ],
            [
                ("admin", "=", 1),
                ("admin", "=", 1),
                "|",
                ("admin", "=", 1),
                ("admin", "=", 1),
                ("skills", "=", 2),
            ],
        ]
        fields_to_remove = [["skills"], ["admin", "skills"]]
        expected_results = [
            [
                [("admin", "=", True)],
                [("admin", "=", True), ("admin", "=", True)],
                [("admin", "=", True)],
                [("admin", "=", True)],
                [
                    "|",
                    "|",
                    ("admin", "=", 1),
                    ("admin", "=", True),
                    ("admin", "=", True),
                ],
                [
                    "|",
                    "|",
                    "!",
                    ("admin", "=", 1),
                    ("admin", "=", True),
                    "!",
                    ("admin", "=", True),
                ],
                [("admin", "=", True)],
                [
                    ["start_datetime", "<=", "2022-12-17 22:59:59"],
                    ["end_datetime", ">=", "2022-12-10 23:00:00"],
                ],
                [
                    ("admin", "=", 1),
                    ("admin", "=", 1),
                    "|",
                    ("admin", "=", 1),
                    ("admin", "=", 1),
                ],
            ],
            [
                [],
                [],
                [],
                [],
                [],
                [],
                [],
                [
                    ["start_datetime", "<=", "2022-12-17 22:59:59"],
                    ["end_datetime", ">=", "2022-12-10 23:00:00"],
                ],
                [],
            ],
        ]
        for idx, fields in enumerate(fields_to_remove):
            results = [
                utils.filter_domain_leaf(dom, lambda field, _f=fields: field not in _f)
                for dom in domains
            ]
            self.assertEqual(
                results, [Domain(expected) for expected in expected_results[idx]]
            )

        self.assertEqual(
            Domain("field4", "!=", "test"),
            utils.filter_domain_leaf(
                [
                    "|",
                    ("field1", "in", [1, 2]),
                    "!",
                    ("field2", "=", False),
                    ("field3", "!=", "test"),
                ],
                lambda field: field == "field3",
                field_name_mapping={"field3": "field4"},
            ),
        )

    def test_resource_schedule_exception_compute_date_to(self):
        date_from = Datetime.from_string("2024-05-01 00:00:00")
        date_to = Datetime.from_string("2024-05-03 23:59:59")
        leave = self.env["resource.schedule.exception"].create(
            {
                "date_from": date_from,
                "date_to": date_to,
            }
        )

        leave.date_from -= relativedelta(minutes=5)
        self.assertEqual(
            leave.date_to, date_to, "date_to shouldn't get recomputed if still valid"
        )

        leave.date_from += relativedelta(years=5)
        self.assertGreater(
            leave.date_to, date_to, "date_to should get recomputed when invalid"
        )

    def test_resource_creation_with_date_from(self):
        """The form collects local days and hours, and stores the instants.

        The exception's zone is the schedule's, so what a reader types is not read
        in the reader's own zone: 08:00 on this calendar is 08:00 there.
        """
        with Form(self.env["resource.schedule.exception"]) as res:
            res.calendar_id = self.env.company.resource_calendar_id
            res.local_date_from = date(2026, 3, 4)
            res.local_hour_from = 8.0
            res.local_date_to = date(2026, 3, 4)
            res.local_hour_to = 17.0

            self.assertFalse(res.id, "The resource does not have an id before saving")
            exception = res.save()
            self.assertTrue(exception.id, "The resource was successfully created")

        tz = timezone(exception.tz)
        self.assertEqual(
            exception.date_from,
            datetime(2026, 3, 4, 8, 0, tzinfo=tz).astimezone(UTC).replace(tzinfo=None),
        )
        self.assertEqual(
            exception.date_to,
            datetime(2026, 3, 4, 17, 0, tzinfo=tz).astimezone(UTC).replace(tzinfo=None),
        )

    def test_an_exception_entered_as_a_day_covers_that_whole_local_day(self):
        with Form(self.env["resource.schedule.exception"]) as res:
            res.calendar_id = self.env.company.resource_calendar_id
            res.local_date_from = date(2026, 3, 4)
            exception = res.save()

        tz = timezone(exception.tz)
        self.assertEqual(
            exception.date_from,
            datetime(2026, 3, 4, 0, 0, tzinfo=tz).astimezone(UTC).replace(tzinfo=None),
        )
        self.assertEqual(
            exception.date_to,
            datetime(2026, 3, 4, 23, 59, 59, tzinfo=tz)
            .astimezone(UTC)
            .replace(tzinfo=None),
        )
