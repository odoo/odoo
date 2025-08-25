from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator


class Slovakia:
    country_code = "SK"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_republic_day_holiday,
            self._compute_epiphany_holiday,
            self._compute_labor_day_holiday,
            self._compute_victory_over_fascism_day,
            self._compute_st_cyril_methodius_day,
            self._compute_national_uprising_day,
            self._compute_our_lady_of_sorrows_day,
            self._compute_all_saints_day_holiday,
            self._compute_christmas_eve_holiday,
            self._compute_christmas_day_holiday,
            self._compute_st_stephens_day_holiday,

            # Movable (Easter-based) — docstrings only; return None
            self._compute_good_friday_holiday,
            self._compute_easter_monday_holiday,
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

    def _compute_republic_day_holiday(self, year: int):
        """Republic Day — fixed date: January 1."""
        return {date(year, 1, 1): "Republic Day"}

    def _compute_epiphany_holiday(self, year: int):
        """Epiphany — fixed date: January 6."""
        return {date(year, 1, 6): "Epiphany"}

    def _compute_labor_day_holiday(self, year: int):
        """Labor Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labor Day"}

    def _compute_victory_over_fascism_day(self, year: int):
        """Day of Victory Over Fascism — fixed date: May 8."""
        return {date(year, 5, 8): "Day of Victory Over Fascism"}

    def _compute_st_cyril_methodius_day(self, year: int):
        """St. Cyril & St. Methodius Day — fixed date: July 5."""
        return {date(year, 7, 5): "St. Cyril & St. Methodius Day"}

    def _compute_national_uprising_day(self, year: int):
        """National Uprising Day — fixed date: August 29."""
        return {date(year, 8, 29): "National Uprising Day"}

    def _compute_our_lady_of_sorrows_day(self, year: int):
        """Day of Our Lady of Sorrows — fixed date: September 15."""
        return {date(year, 9, 15): "Day of Our Lady of Sorrows"}

    def _compute_all_saints_day_holiday(self, year: int):
        """All Saints' Day — fixed date: November 1."""
        return {date(year, 11, 1): "All Saints' Day"}

    def _compute_christmas_eve_holiday(self, year: int):
        """Christmas Eve — fixed date: December 24."""
        return {date(year, 12, 24): "Christmas Eve"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_st_stephens_day_holiday(self, year: int):
        """St. Stephen's Day — fixed date: December 26."""
        return {date(year, 12, 26): "St. Stephen's Day"}

    # -------------------------------
    # Movable (Easter-based) holidays — stubs
    # -------------------------------

    def _compute_good_friday_holiday(self, year: int):
        """Good Friday — Friday before Easter Sunday (movable; requires Easter calculation)."""
        return {self.gregorian_calendar.compute_good_friday(year): "Good Friday"}

    def _compute_easter_monday_holiday(self, year: int):
        """Easter Monday — Monday after Easter Sunday (movable)."""
        return {self.gregorian_calendar.compute_easter_monday(year): "Easter Monday"}
