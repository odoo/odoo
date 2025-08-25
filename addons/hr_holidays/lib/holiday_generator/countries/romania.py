from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator


class Romania:
    country_code = "RO"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,
            self._compute_day_after_new_years_day_holiday,
            self._compute_epiphany_holiday,
            self._compute_synaxis_of_st_john_holiday,
            self._compute_unification_day_holiday,
            self._compute_labour_day_holiday,
            self._compute_childrens_day_holiday,

            # Orthodox Easter-related
            self._compute_orthodox_good_friday_holiday,
            self._compute_orthodox_easter_day_holiday,
            self._compute_orthodox_easter_monday_holiday,
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

    def _compute_day_after_new_years_day_holiday(self, year: int):
        """Day after New Year's Day — fixed date: January 2."""
        return {date(year, 1, 2): "Day after New Year's Day"}

    def _compute_epiphany_holiday(self, year: int):
        """Epiphany — fixed date: January 6."""
        return {date(year, 1, 6): "Epiphany"}

    def _compute_synaxis_of_st_john_holiday(self, year: int):
        """Synaxis of St. John the Baptist — fixed date: January 7."""
        return {date(year, 1, 7): "Synaxis of St. John the Baptist"}

    def _compute_unification_day_holiday(self, year: int):
        """Unification Day — fixed date: January 24."""
        return {date(year, 1, 24): "Unification Day"}

    def _compute_labour_day_holiday(self, year: int):
        """Labor Day / May Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labor Day / May Day"}

    def _compute_childrens_day_holiday(self, year: int):
        """Children's Day — fixed date: June 1."""
        return {date(year, 6, 1): "Children's Day"}

    # -------------------------------
    # Orthodox Easter-related (movable) — stubs
    # -------------------------------

    def _compute_orthodox_good_friday_holiday(self, year: int):
        """
        Orthodox Good Friday — Friday before Orthodox Easter Sunday.
        Date is calculated per Orthodox (Julian-based) computus and varies yearly.
        """
        return {self.gregorian_calendar.compute_orthodox_good_friday(year): "Orthodox Good Friday"}

    def _compute_orthodox_easter_day_holiday(self, year: int):
        """
        Orthodox Easter Day — Christian movable feast following the Orthodox computus.
        Date varies annually and can differ from Western Easter.
        """
        return {self.gregorian_calendar.compute_orthodox_easter(year): "Orthodox Easter Day"}

    def _compute_orthodox_easter_monday_holiday(self, year: int):
        """
        Orthodox Easter Monday — Monday after Orthodox Easter Sunday.
        Movable; follows the same Orthodox Easter calculation.
        """
        return {self.gregorian_calendar.compute_orthodox_easter_monday(year): "Orthodox Easter Monday"}
