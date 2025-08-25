from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator


class Australia:
    country_code = "AU"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            self._compute_new_years_day_holiday,
            self._compute_australia_day_holiday,
            self._compute_anzac_day_holiday,
            self._compute_christmas_day_holiday,
            self._compute_boxing_day_holiday,
            self._compute_good_friday_holiday,       # Easter - 2 days (variable)
            self._compute_easter_monday_holiday,     # Easter + 1 day (variable)
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
    # Static date holidays
    # -------------------------------

    def _compute_new_years_day_holiday(self, year: int):
        return {date(year, 1, 1): "New Year's Day"}

    def _compute_australia_day_holiday(self, year: int):
        return {date(year, 1, 26): "Australia Day"}

    def _compute_anzac_day_holiday(self, year: int):
        return {date(year, 4, 25): "ANZAC Day"}

    def _compute_christmas_day_holiday(self, year: int):
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_boxing_day_holiday(self, year: int):
        return {date(year, 12, 26): "Boxing Day"}

    # -------------------------------
    # Calculated / variable-date holidays
    # -------------------------------

    def _compute_good_friday_holiday(self, year: int):
        """
        Good Friday:
            Rule: Friday before Easter Sunday (Easter - 2 days).
            Requires an Easter calculation (Gregorian computus) to implement.
        """
        return {self.gregorian_calendar.compute_good_friday(year): "Good Friday"}

    def _compute_easter_monday_holiday(self, year: int):
        """
        Easter Monday:
            Rule: Monday after Easter Sunday (Easter + 1 day).
            Requires an Easter calculation (Gregorian computus) to implement.
        """
        return {self.gregorian_calendar.compute_easter_monday(year): "Easter Monday"}
