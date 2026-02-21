# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, UTC, timedelta
from zoneinfo import ZoneInfo

from odoo import fields
from odoo.tests.common import TransactionCase


class TestResourceCommon(TransactionCase):
    @classmethod
    def datetime_tz(cls, year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        """ Return a `datetime` object with a given timezone (if given). """
        dt = datetime(year, month, day, hour, minute, second, microsecond)
        return dt.replace(tzinfo=ZoneInfo(tzinfo)) if tzinfo else dt

    @classmethod
    def datetime_str(cls, year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        """ Return a fields.Datetime value with the given timezone. """
        dt = datetime(year, month, day, hour, minute, second, microsecond)
        if tzinfo:
            dt = dt.replace(tzinfo=ZoneInfo(tzinfo)).astimezone(UTC)
        return fields.Datetime.to_string(dt)

    @classmethod
    def _define_calendar(cls, name, attendances):
        return cls.env["resource.calendar"].create(
            {
                "name": name,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "hour_from": att[0],
                            "hour_to": att[1],
                            "dayofweek": str(att[2]),
                        },
                    )
                    for att in attendances
                ],
            },
        )

    @classmethod
    def _define_calendar_2_weeks(cls, name, attendances):
        return cls.env["resource.calendar"].create(
            {
                "name": name,
                'schedule_type': 'variable',
                "attendance_ids": [
                    (5, 0, 0),
                    *[(0, 0, {"hour_from": att[0], "hour_to": att[1], "date": att[2]}) for att in attendances],
                ],
            },
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.tz = "Europe/Brussels"

        # UTC+1 winter, UTC+2 summer
        cls.calendar_jean = cls._define_calendar(
            "40 Hours", [(8, 16, i) for i in range(5)],
        )
        # UTC+6
        cls.calendar_patel = cls._define_calendar(
            "38 Hours",
            sum((((9, 12, i), (13, 17, i)) for i in range(5)), ()),
        )

        cls.calendar_jules = cls._define_calendar_2_weeks(
            "Week 1: 30 Hours - Week 2: 16 Hours",
            [
                *[(8, 16, date(2018, 3, 26) + timedelta(weeks=w)) for w in range(6)],  # Monday Always
                *[(9, 17, date(2018, 3, 27) + timedelta(weeks=w)) for w in range(6) if not w % 2],
                *[(7, 15, date(2018, 3, 28) + timedelta(weeks=w)) for w in range(6) if w % 2],  # Wednesday Week 1
                *[(8, 16, date(2018, 3, 29) + timedelta(weeks=w)) for w in range(6) if w % 2],  # Thursday Week 1
                *[(10, 16, date(2018, 3, 30) + timedelta(weeks=w)) for w in range(6) if w % 2],  # Friday Week 1
                *[(8, 16, date(2021, 6, 28) + timedelta(weeks=w)) for w in range(6)],  # Monday Always
                *[(9, 17, date(2021, 6, 29) + timedelta(weeks=w)) for w in range(6) if not w % 2],  # Tuesday Week 0
                *[(7, 15, date(2021, 6, 30) + timedelta(weeks=w)) for w in range(6) if w % 2],  # Wednesday Week 1
                *[(8, 16, date(2021, 7, 1) + timedelta(weeks=w)) for w in range(6) if w % 2],  # Thursday Week 1
                *[(10, 16, date(2021, 7, 2) + timedelta(weeks=w)) for w in range(6) if w % 2],  # Friday Week 1
            ],
        )

        # UTC-8 winter, UTC-7 summer
        cls.calendar_john = cls._define_calendar(
            "8+12 Hours",
            [(8, 16, 1), (8, 13, 4), (16, 23, 4)],
        )

        cls.calendar_paul = cls._define_calendar(
            "Morning and evening shifts",
            sum((((2, 7, i), (10, 16, i)) for i in range(5)), ()),
        )

        cls.calendar_bob = cls._define_calendar(
            "Calendar with adjacent attendances",
            sum((((8, 12, i), (12, 16, i)) for i in range(5)), ()),
        )

        cls.env.company.resource_calendar_id = cls._define_calendar(
            "Standard 40h", [
                (8, 12, 0), (13, 17, 0),
                (8, 12, 1), (13, 17, 1),
                (8, 12, 2), (13, 17, 2),
                (8, 12, 3), (13, 17, 3),
                (8, 12, 4), (13, 17, 4),
            ]
        )

        # Employee is linked to a resource.resource via resource.mixin
        cls.jean = cls.env["resource.test"].create(
            {
                "name": "Jean",
                "tz": "Europe/Brussels",
                "resource_calendar_id": cls.calendar_jean.id,
            },
        )
        cls.patel = cls.env["resource.test"].create(
            {
                "name": "Patel",
                "tz": "Etc/GMT-6",
                "resource_calendar_id": cls.calendar_patel.id,
            },
        )
        cls.john = cls.env["resource.test"].create(
            {
                "name": "John",
                "tz": "America/Los_Angeles",
                "resource_calendar_id": cls.calendar_john.id,
            },
        )

        cls.jules = cls.env["resource.test"].create(
            {
                "name": "Jules",
                "resource_calendar_id": cls.calendar_jules.id,
            },
        )

        cls.paul = cls.env["resource.test"].create(
            {
                "name": "Paul",
                "tz": "America/Noronha",
                "resource_calendar_id": cls.calendar_paul.id,
            },
        )

        cls.bob = cls.env["resource.test"].create(
            {
                "name": "Bob",
                "tz": "Europe/Brussels",
                "resource_calendar_id": cls.calendar_bob.id,
            },
        )

        cls.two_weeks_resource = cls._define_calendar_2_weeks(
            "Two weeks resource",
            [],
        )
