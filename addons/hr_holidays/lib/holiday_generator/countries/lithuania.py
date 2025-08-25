from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator
from ..calendars.utils.time_utils import nth_weekday


class Lithuania:
    country_code = "LT"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,
            self._compute_independence_day_holiday,
            self._compute_independence_restoration_day,
            self._compute_labour_day_holiday,
            self._compute_st_johns_day_holiday,
            self._compute_king_mindaugas_coronation_day,
            self._compute_assumption_day_holiday,
            self._compute_all_saints_day_holiday,
            self._compute_all_souls_day_holiday,
            self._compute_christmas_eve_holiday,
            self._compute_christmas_day_holiday,
            self._compute_second_day_of_christmas_holiday,

            # Variable / movable holidays
            self._compute_easter_sunday_holiday,
            self._compute_easter_monday_holiday,
            self._compute_mothers_day_holiday,
            self._compute_fathers_day_holiday,
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

    def _compute_independence_day_holiday(self, year: int):
        """Independence Day / National Day — fixed date: February 16."""
        return {date(year, 2, 16): "Independence Day / National Day"}

    def _compute_independence_restoration_day(self, year: int):
        """Independence Restoration Day — fixed date: March 11."""
        return {date(year, 3, 11): "Independence Restoration Day"}

    def _compute_labour_day_holiday(self, year: int):
        """Labour Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labour Day"}

    def _compute_st_johns_day_holiday(self, year: int):
        """St John's Day / Day of Dew (Rasos/Joninės) — fixed date: June 24."""
        return {date(year, 6, 24): "St John's Day/Day of Dew"}

    def _compute_king_mindaugas_coronation_day(self, year: int):
        """King Mindaugas' Coronation Day — fixed date: July 6."""
        return {date(year, 7, 6): "King Mindaugas' Coronation Day"}

    def _compute_assumption_day_holiday(self, year: int):
        """Feast of the Assumption of Mary — fixed date: August 15."""
        return {date(year, 8, 15): "Feast of the Assumption of Mary"}

    def _compute_all_saints_day_holiday(self, year: int):
        """All Saints' Day — fixed date: November 1."""
        return {date(year, 11, 1): "All Saints' Day"}

    def _compute_all_souls_day_holiday(self, year: int):
        """All Souls' Day — fixed date: November 2."""
        return {date(year, 11, 2): "All Souls' Day"}

    def _compute_christmas_eve_holiday(self, year: int):
        """Christmas Eve — fixed date: December 24."""
        return {date(year, 12, 24): "Christmas Eve"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_second_day_of_christmas_holiday(self, year: int):
        """Second Day of Christmas — fixed date: December 26."""
        return {date(year, 12, 26): "Second Day of Christmas"}

    # -------------------------------
    # Variable / movable holidays (stubs)
    # -------------------------------

    def _compute_easter_sunday_holiday(self, year: int):
        """Easter Sunday — Christian movable feast (computed by Gregorian computus)."""
        return {self.gregorian_calendar.compute_easter_sunday(year): "Easter Sunday"}

    def _compute_easter_monday_holiday(self, year: int):
        """Easter Monday — Monday after Easter Sunday (movable)."""
        return {self.gregorian_calendar.compute_easter_monday(year): "Easter Monday"}

    def _compute_mothers_day_holiday(self, year: int):
        """Mothers' Day — First Sunday in May (movable)."""
        return {nth_weekday(year, 5, 6, 1): "Mothers' Day"}

    def _compute_fathers_day_holiday(self, year: int):
        """Fathers' Day — First Sunday in June (movable)."""
        return {nth_weekday(year, 6, 6, 3), "Fathers' Day"}
