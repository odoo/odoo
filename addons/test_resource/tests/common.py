# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from pytz import timezone, utc

from odoo import fields
from odoo.tests.common import TransactionCase


class TestResourceCommon(TransactionCase):
    @classmethod
    def datetime_tz(cls, year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        """ Return a `datetime` object with a given timezone (if given). """
        dt = datetime(year, month, day, hour, minute, second, microsecond)
        return timezone(tzinfo).localize(dt) if tzinfo else dt

    @classmethod
    def datetime_str(cls, year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        """ Return a fields.Datetime value with the given timezone. """
        dt = datetime(year, month, day, hour, minute, second, microsecond)
        if tzinfo:
            dt = timezone(tzinfo).localize(dt).astimezone(utc)
        return fields.Datetime.to_string(dt)

    @classmethod
    def _define_calendar(cls, name, attendances, tz):
        return cls.env["resource.calendar"].create(
            {
                "name": name,
                "tz": tz,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "%s_%d" % (name, index),
                            "hour_from": att[0],
                            "hour_to": att[1],
                            "dayofweek": str(att[2]),
                            "duration_days": att[3],
                        },
                    )
                    for index, att in enumerate(attendances)
                ],
            },
        )

    @classmethod
    def _define_calendar_2_weeks(cls, name, attendances, tz):
        return cls.env["resource.calendar"].create(
            {
                "name": name,
                "tz": tz,
                "two_weeks_calendar": True,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "%s_%d" % (name, index),
                            "hour_from": att[0],
                            "hour_to": att[1],
                            "dayofweek": str(att[2]),
                            "week_type": att[3],
                        },
                    )
                    for index, att in enumerate(attendances)
                ],
            },
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"

        # UTC+1 winter, UTC+2 summer
        cls.calendar_jean = cls._define_calendar(
            "40 Hours", [(8, 16, i, 1) for i in range(5)], "Europe/Brussels",
        )
        # UTC+6
        cls.calendar_patel = cls._define_calendar(
            "38 Hours",
            sum((((9, 12, i, 3 / 7), (13, 17, i, 4 / 7)) for i in range(5)), ()),
            "Etc/GMT-6",
        )
        # UTC-8 winter, UTC-7 summer
        cls.calendar_john = cls._define_calendar(
            "8+12 Hours",
            [(8, 16, 1, 1), (8, 13, 4, 5 / 12), (16, 23, 4, 7 / 12)],
            "America/Los_Angeles",
        )
        # UTC+1 winter, UTC+2 summer
        cls.calendar_jules = cls._define_calendar_2_weeks(
            "Week 1: 30 Hours - Week 2: 16 Hours",
            [
                (8, 16, 0, "0"),
                (9, 17, 1, "0"),
                (8, 16, 0, "1"),
                (7, 15, 2, "1"),
                (8, 16, 3, "1"),
                (10, 16, 4, "1"),
            ],
            "Europe/Brussels",
        )

        cls.calendar_paul = cls._define_calendar(
            "Morning and evening shifts",
            sum((((2, 7, i, 0.5), (10, 16, i, 0.5)) for i in range(5)), ()),
            "America/Noronha",
        )

        cls.calendar_bob = cls._define_calendar(
            "Calendar with adjacent attendances",
            sum((((8, 12, i, 0.5), (12, 16, i, 0.5)) for i in range(5)), ()),
            "Europe/Brussels",
        )

        # Employee is linked to a resource.resource via resource.mixin
        cls.jean = cls.env["resource.test"].create(
            {
                "name": "Jean",
                "resource_calendar_id": cls.calendar_jean.id,
            },
        )
        cls.patel = cls.env["resource.test"].create(
            {
                "name": "Patel",
                "resource_calendar_id": cls.calendar_patel.id,
            },
        )
        cls.john = cls.env["resource.test"].create(
            {
                "name": "John",
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
                "resource_calendar_id": cls.calendar_paul.id,
            },
        )

        cls.bob = cls.env["resource.test"].create(
            {
                "name": "Bob",
                "resource_calendar_id": cls.calendar_bob.id,
            },
        )

        cls.two_weeks_resource = cls._define_calendar_2_weeks(
            "Two weeks resource",
            [
                (8, 16, 0, "0"),
                (8, 16, 1, "0"),
                (8, 16, 2, "0"),
                (8, 16, 3, "0"),
                (8, 16, 4, "0"),
                (8, 16, 0, "1"),
                (8, 16, 1, "1"),
                (8, 16, 2, "1"),
                (8, 16, 3, "1"),
                (8, 16, 4, "1"),
            ],
            "Europe/Brussels",
        )
