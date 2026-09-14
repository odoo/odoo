"""The sample attendance dataset the Attendances app offers on a fresh database.

A month of plausible days for three demo employees, one per check-in mode. It
lives here rather than on `hr.attendance` because none of it is part of what an
attendance is: seven methods of randomised fixture-building on the model made
its own contract harder to read, and gave downstream modules seven override
points that mean nothing outside a demonstration.

`hr.attendance._load_demo_data` is the one entry point.
"""

from calendar import monthrange
from datetime import timedelta
from random import randint

from dateutil.relativedelta import relativedelta

from odoo import fields

_SYSTRAY_USUAL = {"latitude": 51.01, "longitude": 2.82, "city": "Rellemstraat"}
_SYSTRAY_OCCASIONAL = {"latitude": 50.27, "longitude": 5.31, "city": "Waillet"}


def working_days():
    """A weekday's four clock events for each of the last two months or so."""
    now = fields.Datetime.now()
    previous_month = now - relativedelta(months=1)
    days_back = now.day + monthrange(previous_month.year, previous_month.month)[1]
    for offset in range(1, days_back):
        morning_in = now.replace(hour=6, minute=0, second=randint(0, 59)) + timedelta(
            days=-offset, minutes=randint(-2, 3)
        )
        if morning_in.weekday() not in range(5):
            continue
        yield {
            "morning_in": morning_in,
            "morning_out": now.replace(hour=10, minute=0, second=randint(0, 59))
            + timedelta(days=-offset, minutes=randint(-2, -1)),
            "afternoon_in": now.replace(hour=11, minute=0, second=randint(0, 59))
            + timedelta(days=-offset, minutes=randint(-2, -1)),
            "afternoon_out": now.replace(hour=15, minute=0, second=randint(0, 59))
            + timedelta(days=-offset, minutes=randint(1, 3)),
        }


def _day_vals(employee, mode, morning, afternoon, **extra):
    return [
        {
            "employee_id": employee.id,
            "check_in": check_in,
            "check_out": check_out,
            "in_mode": mode,
            "out_mode": mode,
            **extra,
        }
        for check_in, check_out in (morning, afternoon)
    ]


def kiosk_day_vals(employee, day):
    if day["morning_in"].weekday() == 4:
        return []
    if day["morning_in"].isocalendar().week % 2:
        morning_shift, afternoon_shift = timedelta(hours=1), timedelta(hours=-1)
    else:
        morning_shift = timedelta()
        afternoon_shift = timedelta(hours=1, minutes=30)
    return _day_vals(
        employee,
        "kiosk",
        (day["morning_in"] + morning_shift, day["morning_out"]),
        (day["afternoon_in"], day["afternoon_out"] + afternoon_shift),
    )


def systray_day_vals(employee, day):
    where = _SYSTRAY_OCCASIONAL if randint(1, 10) == 1 else _SYSTRAY_USUAL
    return _day_vals(
        employee,
        "systray",
        (day["morning_in"], day["morning_out"]),
        (day["afternoon_in"], day["afternoon_out"]),
        **{
            f"{side}_{key}": value
            for side in ("in", "out")
            for key, value in (
                ("latitude", where["latitude"]),
                ("longitude", where["longitude"]),
                ("location", where["city"]),
                ("ip_address", "127.0.0.1"),
                ("browser", "chrome"),
            )
        },
    )


def manual_day_vals(employee, day):
    return _day_vals(
        employee,
        "manual",
        (day["morning_in"] + timedelta(minutes=randint(-10, -5)), day["morning_out"]),
        (
            day["afternoon_in"],
            day["afternoon_out"] + timedelta(hours=1, minutes=randint(-20, 10)),
        ),
    )


def attendance_vals(env):
    by_employee = (
        (env.ref("hr.employee_eg"), kiosk_day_vals),
        (env.ref("hr.employee_mw"), systray_day_vals),
        (env.ref("hr.employee_sj"), manual_day_vals),
    )
    return [
        vals
        for day in working_days()
        for employee, build in by_employee
        for vals in build(employee, day)
    ]
