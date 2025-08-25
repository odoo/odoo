from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator


class Netherlands:
    country_code = "NL"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,
            self._compute_liberation_day_holiday,
            self._compute_christmas_day_holiday,
            self._compute_second_day_of_christmas_holiday,

            # Movable / observed (docstrings only; return None)
            self._compute_kings_birthday_holiday,         # 27 Apr (observed 26 Apr if 27th is Sunday)
            self._compute_good_friday_holiday,            # Friday before Easter
            self._compute_easter_sunday_holiday,          # Easter Sunday
            self._compute_easter_monday_holiday,          # Easter Monday
            self._compute_ascension_day_holiday,          # Easter + 39 days (Thu)
            self._compute_whit_sunday_holiday,            # Pentecost Sunday (Easter + 49)
            self._compute_whit_monday_holiday,            # Pentecost Monday (Easter + 50)
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

    def _compute_liberation_day_holiday(self, year: int):
        """Liberation Day — fixed date: May 5."""
        return {date(year, 5, 5): "Liberation Day"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_second_day_of_christmas_holiday(self, year: int):
        """Second Day of Christmas — fixed date: December 26."""
        return {date(year, 12, 26): "Second Day of Christmas"}

    # -------------------------------
    # Movable / observed holidays (stubs)
    # -------------------------------

    def _compute_kings_birthday_holiday(self, year: int):
        """
        King's Birthday (Koningsdag):
            Rule: April 27, but observed on April 26 if April 27 falls on a Sunday.
        """
        kings_day = date(year, 4, 27)
        if kings_day.weekday() == 6:  # Sunday
            kings_day = date(year, 4, 26)
        return {kings_day: "King's Birthday"}

    def _compute_good_friday_holiday(self, year: int):
        """Good Friday — Friday before Easter Sunday (movable; requires Easter calculation)."""
        return {self.gregorian_calendar.compute_good_friday(year): "Good Friday"}

    def _compute_easter_sunday_holiday(self, year: int):
        """Easter Sunday — Christian movable feast (computed by Gregorian computus)."""
        return {self.gregorian_calendar.compute_western_easter(year): "Easter Sunday"}

    def _compute_easter_monday_holiday(self, year: int):
        """Easter Monday — Monday after Easter Sunday (movable)."""
        return {self.gregorian_calendar.compute_easter_monday(year): "Easter Monday"}

    def _compute_ascension_day_holiday(self, year: int):
        """Ascension Day — 39 days after Easter Sunday (Thursday; movable)."""
        return {self.gregorian_calendar.compute_ascension(year): "Ascension Day"}

    def _compute_whit_sunday_holiday(self, year: int):
        """Whit Sunday (Pentecost) — 49 days after Easter Sunday (movable)."""
        return {self.gregorian_calendar.compute_pentecost(year): "Whit Sunday"}

    def _compute_whit_monday_holiday(self, year: int):
        """Whit Monday (Pentecost Monday) — 50 days after Easter Sunday (movable)."""
        return {self.gregorian_calendar.compute_white_monday(year): "Whit Monday"}
