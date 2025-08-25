from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator


class Luxembourg:
    country_code = "LU"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,
            self._compute_labor_day_holiday,
            self._compute_europe_day_holiday,
            self._compute_national_day_holiday,
            self._compute_assumption_day_holiday,
            self._compute_all_saints_day_holiday,
            self._compute_christmas_day_holiday,
            self._compute_st_stephens_day_holiday,

            # Movable (Easter-based) holidays
            self._compute_easter_monday_holiday,     # Easter + 1 day
            self._compute_ascension_day_holiday,     # Easter + 39 days
            self._compute_whit_monday_holiday,       # Easter + 50 days
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
                    results[d] = f"{results[d]}; {name}"
                else:
                    results[d] = name
        return results

    # -------------------------------
    # Fixed-date holidays (every year)
    # -------------------------------

    def _compute_new_years_day_holiday(self, year: int):
        """New Year's Day — fixed date: January 1."""
        return {date(year, 1, 1): "New Year's Day"}

    def _compute_labor_day_holiday(self, year: int):
        """Labor Day / May Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labor Day / May Day"}

    def _compute_europe_day_holiday(self, year: int):
        """Europe Day — fixed date: May 9 (public holiday in Luxembourg)."""
        return {date(year, 5, 9): "Europe Day"}

    def _compute_national_day_holiday(self, year: int):
        """National Day — fixed date: June 23."""
        return {date(year, 6, 23): "National Day"}

    def _compute_assumption_day_holiday(self, year: int):
        """Assumption of Mary — fixed date: August 15."""
        return {date(year, 8, 15): "Assumption of Mary"}

    def _compute_all_saints_day_holiday(self, year: int):
        """All Saints' Day — fixed date: November 1."""
        return {date(year, 11, 1): "All Saints' Day"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_st_stephens_day_holiday(self, year: int):
        """St Stephen's Day — fixed date: December 26."""
        return {date(year, 12, 26): "St Stephen's Day"}

    # -------------------------------
    # Movable (Easter-based) holidays
    # -------------------------------

    def _compute_easter_monday_holiday(self, year: int):
        """Easter Monday — Monday after Easter Sunday."""
        return {self.gregorian_calendar.compute_easter_monday(year): "Easter Monday"}

    def _compute_ascension_day_holiday(self, year: int):
        """Ascension Day — 39 days after Easter Sunday (Thursday; movable)."""
        return {self.gregorian_calendar.compute_ascension(year): "Ascension Day"}

    def _compute_whit_monday_holiday(self, year: int):
        """Whit Monday (Pentecost Monday) — 50 days after Easter Sunday (movable)."""
        return {self.gregorian_calendar.compute_white_monday(year): "Whit Monday"}
