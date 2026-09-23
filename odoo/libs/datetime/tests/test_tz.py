import unittest
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from odoo.libs.datetime.tz import country_timezones, timezone


class TestTimezone(unittest.TestCase):
    def test_valid_name(self):
        self.assertIsInstance(timezone("Europe/Paris"), ZoneInfo)

    def test_unknown_name_raises_zoneinfo_not_found(self):
        with self.assertRaises(ZoneInfoNotFoundError):
            timezone("Not/AZone")

    def test_legacy_turkey_alias_resolves(self):
        self.assertIsInstance(timezone("Turkey"), ZoneInfo)

    def test_utc_is_case_insensitive_like_pytz(self):
        for spelling in ("UTC", "utc", "Utc", "uTc"):
            with self.subTest(spelling=spelling):
                self.assertEqual(timezone(spelling), ZoneInfo("UTC"))

    def test_case_insensitivity_does_not_leak_to_other_zones(self):
        with self.assertRaises(ZoneInfoNotFoundError):
            timezone("europe/paris")


class TestCountryTimezones(unittest.TestCase):
    def test_lookup(self):
        self.assertIn("America/New_York", country_timezones()["US"])
        self.assertEqual(country_timezones()["JP"], ("Asia/Tokyo",))

    def test_mapping_is_not_writable(self):
        with self.assertRaises(TypeError):
            country_timezones()["ZZ"] = ("Nowhere/Land",)  # type: ignore[index]

    def test_zone_lists_are_not_writable(self):
        with self.assertRaises(AttributeError):
            country_timezones()["US"].append("Bogus/Zone")  # type: ignore[attr-defined]

    def test_repeated_calls_are_consistent(self):
        first = country_timezones()
        self.assertIs(first, country_timezones())
        self.assertEqual(first["US"], country_timezones()["US"])


if __name__ == "__main__":
    unittest.main()


def test_localize_standard_reads_a_repeated_hour_outside_daylight_saving():
    from datetime import UTC, datetime, timedelta
    from zoneinfo import ZoneInfo

    from odoo.libs.datetime.tz import localize_standard

    cases = [
        # zone, repeated wall time, offset of the instant outside daylight saving
        ("Europe/Brussels", datetime(2024, 10, 27, 2, 30), timedelta(hours=1)),
        # tzdata models Irish winter as negative DST: IST is the standard side
        ("Europe/Dublin", datetime(2024, 10, 27, 1, 30), timedelta(hours=1)),
        ("Australia/Lord_Howe", datetime(2024, 4, 7, 1, 45), timedelta(hours=10.5)),
    ]
    for name, wall, offset in cases:
        localized = localize_standard(wall, ZoneInfo(name))
        assert localized.utcoffset() == offset, name
        assert (
            localized.astimezone(UTC).astimezone(ZoneInfo(name)).replace(tzinfo=None)
            == wall
        )


def test_localize_standard_moves_a_skipped_wall_time_by_the_earlier_offset():
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from odoo.libs.datetime.tz import localize_standard

    skipped = localize_standard(
        datetime(2024, 3, 31, 2, 30), ZoneInfo("Europe/Brussels")
    )
    assert skipped.utcoffset() == timedelta(hours=1)
