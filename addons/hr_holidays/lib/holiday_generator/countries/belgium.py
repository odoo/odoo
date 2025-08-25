from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator


class Belgium:
    country_code = "BE"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            # Static dates
            self._compute_new_years_day_holiday,
            self._compute_labor_day_holiday,
            self._compute_belgian_national_day_holiday,
            self._compute_assumption_day_holiday,
            self._compute_all_saints_day_holiday,
            self._compute_armistice_day_holiday,
            self._compute_christmas_day_holiday,

            # Variable (Christian feasts depending on Easter)
            self._compute_easter_monday_holiday,
            self._compute_ascension_day_holiday,
            self._compute_whit_monday_holiday,
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

    def _compute_labor_day_holiday(self, year: int):
        return {date(year, 5, 1): "Labor Day"}

    def _compute_belgian_national_day_holiday(self, year: int):
        return {date(year, 7, 21): "Belgian National Day"}

    def _compute_assumption_day_holiday(self, year: int):
        return {date(year, 8, 15): "Assumption of Mary"}

    def _compute_all_saints_day_holiday(self, year: int):
        return {date(year, 11, 1): "All Saints' Day"}

    def _compute_armistice_day_holiday(self, year: int):
        return {date(year, 11, 11): "Armistice Day"}

    def _compute_christmas_day_holiday(self, year: int):
        return {date(year, 12, 25): "Christmas Day"}

    # -------------------------------
    # Variable / movable holidays
    # -------------------------------

    def _compute_easter_monday_holiday(self, year: int):
        """
        Easter Monday:
        Rule: Easter Sunday + 1 day.
        """
        return {self.gregorian_calendar.compute_easter_monday(year): "Easter Monday"}

    def _compute_ascension_day_holiday(self, year: int):
        """
        Ascension Day:
          Rule: Easter Sunday + 39 days (Thursday).
        """
        return {self.gregorian_calendar.compute_ascension(year): "Ascension Day"}

    def _compute_whit_monday_holiday(self, year: int):
        """
        Whit Monday (Pentecost Monday):
          Rule: Easter Sunday + 50 days (Monday).
        """
        return {self.gregorian_calendar.compute_white_monday(year): "Whit Monday"}
