import os
import pathlib
import subprocess
import sys
import textwrap
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

from odoo.libs.datetime.date_utils import date_range, next_after, occurrences_after
from odoo.libs.datetime.tz import timezone

BRUSSELS = ZoneInfo("Europe/Brussels")


class TestMonthEndsDoNotDrift:
    def test_a_range_from_the_31st_returns_to_the_31st(self):
        assert list(date_range(date(2024, 1, 31), date(2024, 6, 30))) == [
            date(2024, 1, 31),
            date(2024, 2, 29),
            date(2024, 3, 31),
            date(2024, 4, 30),
            date(2024, 5, 31),
            date(2024, 6, 30),
        ]

    def test_datetimes_do_not_drift_either(self):
        got = list(date_range(datetime(2023, 1, 31, 8), datetime(2023, 4, 30, 8)))
        assert [value.day for value in got] == [31, 28, 31, 30]


class TestSubDayStepsAreElapsedTime:
    def test_the_spring_gap_is_not_counted_twice(self):
        start = datetime(2024, 3, 31, 0, tzinfo=BRUSSELS)
        end = datetime(2024, 3, 31, 5, tzinfo=BRUSSELS)
        got = [
            value.astimezone(UTC).hour
            for value in date_range(start, end, relativedelta(hours=1))
        ]
        assert got == [23, 0, 1, 2, 3]

    def test_the_autumn_fold_is_not_skipped(self):
        start = datetime(2024, 10, 27, 0, tzinfo=BRUSSELS)
        end = datetime(2024, 10, 27, 4, tzinfo=BRUSSELS)
        got = [
            value.astimezone(UTC).hour
            for value in date_range(start, end, relativedelta(hours=1))
        ]
        assert got == [22, 23, 0, 1, 2, 3]

    def test_values_keep_the_start_zone(self):
        start = datetime(2024, 3, 31, 0, tzinfo=BRUSSELS)
        got = list(
            date_range(start, start + relativedelta(hours=2), relativedelta(hours=1))
        )
        assert {value.tzinfo for value in got} == {BRUSSELS}

    def test_a_daily_step_is_still_wall_time(self):
        start = datetime(2024, 3, 30, 12, tzinfo=BRUSSELS)
        end = datetime(2024, 4, 1, 12, tzinfo=BRUSSELS)
        got = list(date_range(start, end, relativedelta(days=1)))
        assert [value.hour for value in got] == [12, 12, 12]


class TestUtcSpellings:
    @pytest.mark.parametrize("other", [ZoneInfo("UTC"), ZoneInfo("Etc/UTC")])
    def test_any_utc_zone_matches_datetime_utc(self, other):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 3, 1, tzinfo=other)
        assert len(list(date_range(start, end))) == 3

    def test_the_timezone_helper_utc_matches_datetime_utc(self):
        start = datetime(2024, 1, 1, tzinfo=timezone("UTC"))
        end = datetime(2024, 1, 1, 3, tzinfo=UTC)
        assert len(list(date_range(start, end, relativedelta(hours=1)))) == 4


class TestMixedTypes:
    def test_a_date_and_a_datetime_are_refused_with_value_error(self):
        with pytest.raises(ValueError, match="both date or both datetime"):
            list(date_range(date(2024, 1, 1), datetime(2024, 3, 1)))
        with pytest.raises(ValueError, match="both date or both datetime"):
            list(date_range(datetime(2024, 1, 1), date(2024, 3, 1)))


class TestExactCadenceNeedsDatetimes:
    @pytest.mark.parametrize("unit", ["minute", "hour"])
    def test_a_date_with_an_exact_unit_is_refused(self, unit):
        with pytest.raises(TypeError, match="needs datetimes"):
            next_after(date(2024, 1, 1), date(2024, 1, 1), 1, unit)

    def test_a_date_with_a_calendar_unit_still_works(self):
        got = next(occurrences_after(date(2024, 1, 1), date(2024, 1, 1), 1, "day"))
        assert got == date(2024, 1, 2)


def test_to_timezone_none_reads_a_naive_value_as_utc_whatever_the_process_zone():
    program = textwrap.dedent(
        """
        from datetime import datetime
        from odoo.libs.datetime.date_utils import to_timezone
        print(to_timezone(None)(datetime(2024, 1, 1, 12)).isoformat())
        """
    )
    root = str(pathlib.Path(__file__).resolve().parents[4])
    out = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        check=True,
        cwd=root,
        env={**os.environ, "TZ": "America/Mexico_City", "PYTHONPATH": root},
    )
    assert out.stdout.strip() == "2024-01-01T12:00:00"


def test_a_step_with_absolute_fields_still_yields_start_first():
    from dateutil.relativedelta import FR

    assert list(
        date_range(
            date(2024, 1, 15), date(2024, 1, 20), relativedelta(months=1, day=31)
        )
    ) == [date(2024, 1, 15)]
    first = next(
        date_range(
            date(2024, 1, 10), date(2024, 3, 1), relativedelta(months=1, weekday=FR(-1))
        )
    )
    assert first == date(2024, 1, 10)


@pytest.mark.parametrize("zone", ["GMT", "Etc/GMT", "fixed"])
def test_gmt_counts_as_utc(zone):
    from datetime import timedelta
    from datetime import timezone as fixed_offset

    tz = fixed_offset(timedelta(0)) if zone == "fixed" else ZoneInfo(zone)
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 1, 3, tzinfo=tz)
    assert len(list(date_range(start, end, relativedelta(hours=1)))) == 4
