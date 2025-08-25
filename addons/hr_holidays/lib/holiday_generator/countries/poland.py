from datetime import date
from typing import Dict


from ..calendars.gregorian_calendar import ChristianHolidayGenerator

class Poland:
    country_code = "PL"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,
            self._compute_epiphany_holiday,
            self._compute_labour_day_holiday,
            self._compute_constitution_day_holiday,
            self._compute_assumption_day_holiday,
            self._compute_all_saints_day_holiday,
            self._compute_independence_day_holiday,
            self._compute_christmas_eve_holiday,
            self._compute_christmas_day_holiday,
            self._compute_second_day_of_christmas_holiday,

            # Movable (Easter-based) — docstring only, return None
            self._compute_easter_sunday_holiday,
            self._compute_easter_monday_holiday,
            self._compute_whit_sunday_holiday,
            self._compute_corpus_christi_holiday,
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

    def _compute_epiphany_holiday(self, year: int):
        """Epiphany — fixed date: January 6."""
        return {date(year, 1, 6): "Epiphany"}

    def _compute_labour_day_holiday(self, year: int):
        """Labor Day / May Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labor Day / May Day"}

    def _compute_constitution_day_holiday(self, year: int):
        """Constitution Day — fixed date: May 3."""
        return {date(year, 5, 3): "Constitution Day"}

    def _compute_assumption_day_holiday(self, year: int):
        """Assumption of Mary — fixed date: August 15."""
        return {date(year, 8, 15): "Assumption of Mary"}

    def _compute_all_saints_day_holiday(self, year: int):
        """All Saints' Day — fixed date: November 1."""
        return {date(year, 11, 1): "All Saints' Day"}

    def _compute_independence_day_holiday(self, year: int):
        """Independence Day — fixed date: November 11."""
        return {date(year, 11, 11): "Independence Day"}

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
    # Movable (Easter-based) holidays (stubs)
    # -------------------------------

    def _compute_easter_sunday_holiday(self, year: int):
        """Easter Sunday — Christian movable feast (computed by Gregorian computus)."""
        return {self.gregorian_calendar.compute_easter_sunday(year): "Easter Sunday"}

    def _compute_easter_monday_holiday(self, year: int):
        """Easter Monday — Monday after Easter Sunday (movable)."""
        return {self.gregorian_calendar.compute_easter_monday(year): "Easter Monday"}

    def _compute_whit_sunday_holiday(self, year: int):
        """Whit Sunday (Pentecost) — 49 days after Easter Sunday (movable)."""
        return {self.gregorian_calendar.compute_pentecost(year): "Whit Sunday"}

    def _compute_corpus_christi_holiday(self, year: int):
        """Corpus Christi — Thursday after Trinity Sunday (Easter + 60 days)."""
        return {self.gregorian_calendar.compute_corpus_christi(year): "Corpus Christi"}
