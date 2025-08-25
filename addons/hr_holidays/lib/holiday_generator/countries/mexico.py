from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator
from ..calendars.utils.time_utils import nth_weekday


class Mexico:
    country_code = "MX"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,         # 1 Jan
            self._compute_constitution_day_holiday,      # 5 Feb (observed on first Monday of Feb; fixed in list as 3 Feb 2025)
            self._compute_benito_juarez_birthday,        # 21 Mar (observed on 3rd Monday of March; 17 Mar 2025)
            self._compute_labor_day_holiday,             # 1 May
            self._compute_independence_day_holiday,      # 16 Sep
            self._compute_revolution_day_memorial,       # 20 Nov (observed on 3rd Monday of November; 17 Nov 2025)
            self._compute_day_of_virgin_guadalupe,       # 12 Dec
            self._compute_christmas_day_holiday,         # 25 Dec

            # Variable / movable (docstring only; return None)
            self._compute_maundy_thursday_holiday,
            self._compute_good_friday_holiday,
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
    # Fixed-date or observed holidays
    # -------------------------------

    def _compute_new_years_day_holiday(self, year: int):
        """New Year's Day — fixed date: January 1."""
        return {date(year, 1, 1): "New Year's Day"}

    def _compute_constitution_day_holiday(self, year: int) -> Dict[date, str]:
        """
        Constitution Day — officially Feb 5, observed on the first Monday of February.
        """
        return {nth_weekday(year, 2, weekday=0, n=1): "Constitution Day"}

    def _compute_benito_juarez_birthday(self, year: int) -> Dict[date, str]:
        """
        Benito Juárez's Birthday Memorial — officially Mar 21,
        observed on the third Monday of March.
        """
        return {nth_weekday(year, 3, weekday=0, n=3): "Benito Juárez's Birthday Memorial"}

    def _compute_labor_day_holiday(self, year: int):
        """Labor Day / May Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labor Day / May Day"}

    def _compute_independence_day_holiday(self, year: int):
        """Independence Day — fixed date: September 16."""
        return {date(year, 9, 16): "Independence Day"}

    def _compute_revolution_day_memorial(self, year: int):
        """
        Revolution Day Memorial — officially Nov 20, observed on the third Monday of November.
        Example: 2025 observed on Nov 17.
        """
        # Use nth_weekday to get the 3rd Monday (weekday=0) in November
        return {nth_weekday(year, 11, weekday=0, n=3): "Revolution Day Memorial"}

    def _compute_day_of_virgin_guadalupe(self, year: int):
        """Day of the Virgin of Guadalupe — fixed date: December 12."""
        return {date(year, 12, 12): "Day of the Virgin of Guadalupe"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    # -------------------------------
    # Variable / movable holidays (stubs)
    # -------------------------------

    def _compute_maundy_thursday_holiday(self, year: int):
        """Maundy Thursday — Christian movable feast (Thursday before Easter Sunday)."""
        return {self.gregorian_calendar.compute_maundy_thursday(year): "Maundy Thursday"}

    def _compute_good_friday_holiday(self, year: int):
        """Good Friday — Christian movable feast (Friday before Easter Sunday)."""
        return {self.gregorian_calendar.compute_good_friday(year): "Good Friday"}
