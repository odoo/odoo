from datetime import date
from typing import Dict

from ..calendars.utils.time_utils import last_weekday, nth_weekday


class UnitedStates:
    country_code = "US"

    def __init__(self):
        # Static date holidays (fixed Gregorian dates)
        self._public_holiday_computers = [
            self._compute_new_years_day_holiday,
            self._compute_juneteenth_holiday,
            self._compute_independence_day_holiday,
            self._compute_veterans_day_holiday,
            self._compute_christmas_day_holiday,
            self._compute_jimmy_carter_holiday,               # 2025-only
            self._compute_martin_luther_king_jr_day_holiday,  # 3rd Mon Jan
            self._compute_inauguration_day_holiday,           # Jan 20, every 4 yrs (from 1937)
            self._compute_presidents_day_holiday,             # 3rd Mon Feb
            self._compute_memorial_day_holiday,               # Last Mon May
            self._compute_labor_day_holiday,                  # 1st Mon Sep
            self._compute_columbus_day_holiday,               # 2nd Mon Oct
            self._compute_thanksgiving_day_holiday,           # 4th Thu Nov
        ]

    def holidays_for_year(self, year: int) -> Dict[date, str]:
        """
        Collect holidays for the given year.
        Each holiday computer returns a Dict {date: name}.
        Merge them into one big Dict.
        If multiple holidays fall on the same date, merge the names with '; '.
        """
        results: Dict[date, str] = {}
        for fn in self._public_holiday_computers:
            h = fn(year)
            if not h:
                continue
            for d, name in h.items():
                if d in results:
                    # Merge names with '; ' if duplicate date
                    results[d] = f"{results[d]}; {name}"
                else:
                    results[d] = name
        return results

    # -------------------------------
    # Static date holidays
    # -------------------------------

    def _compute_new_years_day_holiday(self, year: int):
        return {date(year, 1, 1): "New Year's Day"}

    def _compute_juneteenth_holiday(self, year: int):
        return {date(year, 6, 19): "Juneteenth"}

    def _compute_independence_day_holiday(self, year: int):
        return {date(year, 7, 4): "Independence Day"}

    def _compute_veterans_day_holiday(self, year: int):
        return {date(year, 11, 11): "Veterans Day"}

    def _compute_christmas_day_holiday(self, year: int):
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_jimmy_carter_holiday(self, year: int):
        # This proclamation was specific to 2025: Thu, Jan 9, 2025.
        # Only include in that year.
        if year == 2025:
            return {date(2025, 1, 9): "National Day of Mourning for Jimmy Carter"}
        return None

    # -------------------------------
    # Calculated holidays
    # -------------------------------

    def _compute_martin_luther_king_jr_day_holiday(self, year: int) -> Dict[date, str]:
        """
            RULE: 3rd Monday in January.
            (If you want to restrict to federal adoption years, add: if year < 1986: return {})
        """
        return {nth_weekday(year, 1, n=3, weekday=0): "Martin Luther King Jr. Day"}

    def _compute_inauguration_day_holiday(self, year: int) -> Dict[date, str]:
        """
            RULE: January 20 every 4 years starting 1937.
            Note: When Jan 20 is a Sunday, the public observance is Jan 21 (Monday).
        """
        if year >= 1937 and (year - 1937) % 4 == 0:
            d = date(year, 1, 20)
            if d.weekday() == 6:  # Sunday
                d = date(year, 1, 21)
            return {d: "Inauguration Day"}
        return None

    def _compute_presidents_day_holiday(self, year: int) -> Dict[date, str]:
        """
            RULE: 3rd Monday in February. (aka Washington's Birthday in US federal law)
        """
        return {nth_weekday(year, 2, n=3, weekday=0): "Presidents' Day"}

    def _compute_memorial_day_holiday(self, year: int) -> Dict[date, str]:
        """
            RULE: Last Monday in May.
        """
        return {last_weekday(year, 5, weekday=0): "Memorial Day"}

    def _compute_labor_day_holiday(self, year: int) -> Dict[date, str]:
        """
            RULE: 1st Monday in September.
        """
        return {nth_weekday(year, 9, n=1, weekday=0): "Labor Day"}

    def _compute_columbus_day_holiday(self, year: int) -> Dict[date, str]:
        """
            RULE: 2nd Monday in October.
        """
        return {nth_weekday(year, 10, n=2, weekday=0): "Columbus Day"}

    def _compute_thanksgiving_day_holiday(self, year: int) -> Dict[date, str]:
        """
            RULE: 4th Thursday in November.
        """
        return {nth_weekday(year, 11, n=4, weekday=3): "Thanksgiving Day"}
