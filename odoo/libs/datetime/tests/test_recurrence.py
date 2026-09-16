import itertools
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

from odoo.libs.datetime.date_utils import (
    Anchor,
    TimeUnit,
    anchor_day,
    get_timedelta,
    next_after,
    next_anchor,
    occurrences_after,
    previous_anchor,
)

NOW = datetime(2026, 9, 12, 10, 30)
PLURAL: dict[TimeUnit, str] = {
    "minute": "minutes",
    "hour": "hours",
    "day": "days",
    "week": "weeks",
    "month": "months",
}


def _cron_next_call(nextcall, now, interval_type, interval_number, tz):
    # `ir.cron._get_next_call` as it stood before it delegated here, with the
    # record's context timezone passed explicitly.
    if interval_type in ("minutes", "hours"):
        interval = timedelta(**{interval_type: interval_number})
        if nextcall <= now:
            steps = (now - nextcall) // interval + 1
            nextcall += steps * interval
        return nextcall
    interval = relativedelta(**{interval_type: interval_number})
    while nextcall <= now:
        local = nextcall.replace(tzinfo=UTC).astimezone(tz)
        nextcall = (local + interval).astimezone(UTC).replace(tzinfo=None)
    return nextcall


class TestNextAfter:
    @pytest.mark.parametrize("unit", list(PLURAL))
    @pytest.mark.parametrize("interval", [1, 3, 17])
    @pytest.mark.parametrize(
        "start",
        [
            NOW - timedelta(days=400, minutes=7),
            NOW - timedelta(hours=5),
            NOW,
            NOW + timedelta(minutes=1),
        ],
    )
    @pytest.mark.parametrize(
        "tz_name", ["UTC", "America/Mexico_City", "Europe/Brussels"]
    )
    def test_matches_the_cron_arithmetic_it_replaced(
        self, unit, interval, start, tz_name
    ):
        tz = ZoneInfo(tz_name)
        expected = _cron_next_call(start, NOW, PLURAL[unit], interval, tz)
        assert next_after(start, NOW, interval, unit, tz) == expected

    def test_result_is_strictly_after(self):
        for unit in PLURAL:
            assert next_after(NOW, NOW, 1, unit) > NOW

    def test_a_future_start_is_its_own_next_occurrence(self):
        start = NOW + timedelta(days=3)
        assert next_after(start, NOW, 2, "week") == start

    def test_daily_steps_keep_the_local_hour_across_dst(self):
        brussels = ZoneInfo("Europe/Brussels")
        start = datetime(2026, 3, 28, 9, 0)  # 10:00 CET, the day before the change
        after = datetime(2026, 3, 28, 12, 0)
        result = next_after(start, after, 1, "day", brussels)
        assert result.replace(tzinfo=UTC).astimezone(brussels).hour == 10
        assert result == datetime(
            2026, 3, 29, 8, 0
        )  # 10:00 CEST, one hour earlier in UTC

    def test_a_month_end_series_does_not_drift(self):
        start = date(2026, 1, 31)
        occurrences = []
        after = start
        for _ in range(4):
            after = next_after(start, after, 1, "month")
            occurrences.append(after)
        assert occurrences == [
            date(2026, 2, 28),
            date(2026, 3, 31),
            date(2026, 4, 30),
            date(2026, 5, 31),
        ]

    def test_dates_step_without_a_timezone(self):
        assert next_after(date(2026, 1, 1), date(2026, 1, 20), 2, "week") == date(
            2026, 1, 29
        )

    def test_rejects_a_non_positive_interval(self):
        with pytest.raises(ValueError, match="positive"):
            next_after(NOW, NOW, 0, "day")


def _walk_occurrences_after(start, after, interval, unit, tz, count):
    local = start.replace(tzinfo=UTC).astimezone(tz)
    found: list[datetime] = []
    k = 0
    while len(found) < count:
        candidate = (local + get_timedelta(interval, unit) * k).astimezone(UTC)
        candidate = candidate.replace(tzinfo=None)
        if candidate > after:
            found.append(candidate)
        k += 1
    return found


class TestOccurrencesAfter:
    @pytest.mark.parametrize("unit", ["day", "week", "month", "year"])
    @pytest.mark.parametrize("interval", [1, 2, 5])
    @pytest.mark.parametrize(
        "start",
        [
            datetime(2026, 1, 31, 23, 30),
            datetime(2024, 2, 29, 8, 0),
            NOW - timedelta(days=3),
            NOW + timedelta(days=40),
        ],
    )
    @pytest.mark.parametrize(
        "tz_name", ["UTC", "America/Mexico_City", "Europe/Brussels"]
    )
    def test_yields_the_series_own_dates_after_the_moment(
        self, unit, interval, start, tz_name
    ):
        tz = ZoneInfo(tz_name)
        yielded = list(
            itertools.islice(occurrences_after(start, NOW, interval, unit, tz), 6)
        )
        assert yielded == _walk_occurrences_after(start, NOW, interval, unit, tz, 6)

    @pytest.mark.parametrize("unit", ["day", "week", "month", "year"])
    def test_a_decades_old_series_lands_on_its_grid(self, unit):
        tz = ZoneInfo("Europe/Brussels")
        start = datetime(1990, 1, 31, 9, 0)
        after = datetime(2026, 3, 30, 12, 0)
        assert (
            next(occurrences_after(start, after, 1, unit, tz))
            == (_walk_occurrences_after(start, after, 1, unit, tz, 1)[0])
        )

    def test_hours_step_exact_time_from_the_start(self):
        start = datetime(2026, 9, 12, 8, 15)
        assert list(itertools.islice(occurrences_after(start, NOW, 1, "hour"), 3)) == [
            datetime(2026, 9, 12, 11, 15),
            datetime(2026, 9, 12, 12, 15),
            datetime(2026, 9, 12, 13, 15),
        ]

    def test_a_future_start_is_the_first_occurrence(self):
        start = NOW + timedelta(days=3)
        assert list(itertools.islice(occurrences_after(start, NOW, 1, "week"), 2)) == [
            start,
            start + timedelta(weeks=1),
        ]


def _accrual_next(frequency, last_call, **anchors):
    # `hr.leave.accrual.level._get_next_date` as it stood before it delegated here.
    d = {k: int(v) for k, v in anchors.items()}
    if frequency == "daily":
        return last_call + relativedelta(days=1)
    if frequency == "weekly":
        return last_call + relativedelta(days=1, weekday=d["week_day"])
    if frequency == "bimonthly":
        first = last_call + relativedelta(day=d["first_day"])
        second = last_call + relativedelta(day=d["second_day"])
        if last_call < first:
            return first
        if last_call < second:
            return second
        return last_call + relativedelta(day=d["first_day"], months=1)
    if frequency == "monthly":
        first = last_call + relativedelta(day=d["first_day"])
        if last_call < first:
            return first
        return last_call + relativedelta(day=d["first_day"], months=1)
    if frequency == "biyearly":
        first = last_call + relativedelta(
            month=d["first_month"], day=d["first_month_day"]
        )
        second = last_call + relativedelta(
            month=d["second_month"], day=d["second_month_day"]
        )
        if last_call < first:
            return first
        if last_call < second:
            return second
        return last_call + relativedelta(
            month=d["first_month"], day=d["first_month_day"], years=1
        )
    first = last_call + relativedelta(month=d["yearly_month"], day=d["yearly_day"])
    if last_call < first:
        return first
    return last_call + relativedelta(
        month=d["yearly_month"], day=d["yearly_day"], years=1
    )


def _accrual_previous(frequency, last_call, **anchors):
    # `_get_previous_date` as it stood, minus the monthly branch's `days=1`: that
    # branch alone returned the day after the previous anchor, so one period
    # measured 30 or 31 days depending on which month a partial start fell in.
    d = {k: int(v) for k, v in anchors.items()}
    if frequency == "daily":
        return last_call
    if frequency == "weekly":
        return last_call + relativedelta(days=-6, weekday=d["week_day"])
    if frequency == "bimonthly":
        first = last_call + relativedelta(day=d["first_day"])
        second = last_call + relativedelta(day=d["second_day"])
        if last_call >= second:
            return second
        if last_call >= first:
            return first
        return last_call + relativedelta(day=d["second_day"], months=-1)
    if frequency == "monthly":
        first = last_call + relativedelta(day=d["first_day"])
        if last_call >= first:
            return first
        return last_call + relativedelta(day=d["first_day"], months=-1)
    if frequency == "biyearly":
        first = last_call + relativedelta(
            month=d["first_month"], day=d["first_month_day"]
        )
        second = last_call + relativedelta(
            month=d["second_month"], day=d["second_month_day"]
        )
        if last_call >= second:
            return second
        if last_call >= first:
            return first
        return last_call + relativedelta(
            month=d["second_month"], day=d["second_month_day"], years=-1
        )
    first = last_call + relativedelta(month=d["yearly_month"], day=d["yearly_day"])
    if last_call >= first:
        return first
    return last_call + relativedelta(
        month=d["yearly_month"], day=d["yearly_day"], years=-1
    )


DATES = [date(2023, 12, 31) + timedelta(days=offset) for offset in range(0, 800, 7)] + [
    date(2024, 2, 28),
    date(2024, 2, 29),
    date(2025, 2, 28),
    date(2026, 1, 31),
    date(2026, 6, 30),
    date(2026, 12, 31),
]

SCHEDULES = [
    ("daily", "day", [], {}),
    *[("weekly", "week", [Anchor(weekday=wd)], {"week_day": wd}) for wd in range(7)],
    *[
        ("monthly", "month", [Anchor(day=day)], {"first_day": day})
        for day in (1, 15, 28, 30, 31)
    ],
    *[
        (
            "bimonthly",
            "month",
            [Anchor(day=first), Anchor(day=second)],
            {"first_day": first, "second_day": second},
        )
        for first, second in ((1, 15), (10, 25), (14, 31), (29, 30))
    ],
    *[
        (
            "yearly",
            "year",
            [Anchor(month=month, day=day)],
            {"yearly_month": month, "yearly_day": day},
        )
        for month, day in ((1, 1), (2, 29), (6, 30), (12, 31))
    ],
    *[
        (
            "biyearly",
            "year",
            [Anchor(month=m1, day=d1), Anchor(month=m2, day=d2)],
            {
                "first_month": m1,
                "first_month_day": d1,
                "second_month": m2,
                "second_month_day": d2,
            },
        )
        for (m1, d1), (m2, d2) in (
            ((1, 1), (7, 1)),
            ((2, 29), (8, 31)),
            ((6, 30), (12, 31)),
        )
    ],
]


class TestAnchored:
    @pytest.mark.parametrize(
        ("frequency", "unit", "anchors", "fields"), SCHEDULES, ids=str
    )
    def test_next_matches_the_accrual_arithmetic_it_replaced(
        self, frequency, unit, anchors, fields
    ):
        for last_call in DATES:
            assert next_anchor(last_call, unit, anchors) == _accrual_next(
                frequency, last_call, **fields
            ), last_call

    @pytest.mark.parametrize(
        ("frequency", "unit", "anchors", "fields"), SCHEDULES, ids=str
    )
    def test_previous_matches_the_accrual_arithmetic(
        self, frequency, unit, anchors, fields
    ):
        for last_call in DATES:
            assert previous_anchor(last_call, unit, anchors) == _accrual_previous(
                frequency, last_call, **fields
            ), last_call

    def test_previous_is_on_or_before_and_next_strictly_after(self):
        anchors = [Anchor(day=10), Anchor(day=25)]
        for day in itertools.islice(DATES, 60):
            assert (
                previous_anchor(day, "month", anchors)
                <= day
                < next_anchor(day, "month", anchors)
            )

    def test_a_day_past_the_month_end_is_clamped_not_skipped(self):
        assert next_anchor(date(2026, 2, 1), "month", [Anchor(day=31)]) == date(
            2026, 2, 28
        )
        assert next_anchor(date(2024, 2, 1), "month", [Anchor(day=31)]) == date(
            2024, 2, 29
        )

    def test_rejects_a_period_without_anchors(self):
        with pytest.raises(ValueError, match="at least one anchor"):
            next_anchor(date(2026, 1, 1), "month", [])

    def test_rejects_an_anchor_missing_its_component(self):
        with pytest.raises(ValueError, match="missing"):
            next_anchor(date(2026, 1, 1), "year", [Anchor(day=1)])


class TestLastDay:
    def test_a_last_day_boundary_is_the_first_of_the_next_month(self):
        last = [Anchor(last_day=True)]
        assert next_anchor(date(2026, 1, 20), "month", last) == date(2026, 2, 1)
        assert next_anchor(date(2026, 1, 31), "month", last) == date(2026, 2, 1)
        assert next_anchor(date(2026, 2, 1), "month", last) == date(2026, 3, 1)
        assert previous_anchor(date(2026, 2, 1), "month", last) == date(2026, 2, 1)
        assert previous_anchor(date(2026, 1, 31), "month", last) == date(2026, 1, 1)

    def test_its_period_is_the_calendar_month_however_long(self):
        last = [Anchor(last_day=True)]
        for month, days in ((1, 31), (2, 28), (4, 30)):
            on = date(2026, month, 10)
            assert (
                next_anchor(on, "month", last) - previous_anchor(on, "month", last)
            ).days == days

    def test_it_names_the_last_day(self):
        last = [Anchor(last_day=True)]
        assert anchor_day(date(2026, 3, 1), "month", last) == date(2026, 2, 28)
        assert anchor_day(date(2024, 3, 1), "month", last) == date(2024, 2, 29)
        assert anchor_day(date(2026, 3, 15), "month", last) == date(2026, 3, 15)

    def test_twice_a_month_on_the_15th_and_the_last_day(self):
        anchors = [Anchor(day=15), Anchor(last_day=True)]
        assert next_anchor(date(2026, 1, 10), "month", anchors) == date(2026, 1, 15)
        assert next_anchor(date(2026, 1, 15), "month", anchors) == date(2026, 2, 1)
        assert previous_anchor(date(2026, 1, 10), "month", anchors) == date(2026, 1, 1)
        assert anchor_day(date(2026, 1, 15), "month", anchors) == date(2026, 1, 15)
        assert anchor_day(date(2026, 2, 1), "month", anchors) == date(2026, 1, 31)

    def test_yearly_on_the_last_day_of_a_month(self):
        february = [Anchor(month=2, last_day=True)]
        assert next_anchor(date(2024, 1, 1), "year", february) == date(2024, 3, 1)
        assert anchor_day(date(2024, 3, 1), "year", february) == date(2024, 2, 29)
        assert anchor_day(date(2024, 4, 1), "year", february) == date(2024, 4, 1)

    def test_the_last_day_of_december_wraps_into_the_next_year(self):
        december = [Anchor(month=12, last_day=True)]
        assert next_anchor(date(2025, 6, 1), "year", december) == date(2026, 1, 1)
        assert previous_anchor(date(2025, 12, 31), "year", december) == date(2025, 1, 1)
        assert anchor_day(date(2026, 1, 1), "year", december) == date(2025, 12, 31)
