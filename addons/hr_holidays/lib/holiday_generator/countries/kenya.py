from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator
from ..calendars.islamic_calendar import IslamicHolidayGenerator
from ..calendars.location import Location


class Kenya:
    country_code = "KE"

    def __init__(self):
        self.location = Location(
            lat=-1.2921,      # degrees (south → negative)
            lon=36.8219,      # degrees (east → positive)
            tz=3.0,          # Kenya Standard Time (UTC+3, no DST)
            height_m=1795.0,  # Nairobi's elevation in meters
            visibility_thresholds=None,
        )
        self.islamic_calendar = IslamicHolidayGenerator(self.location)
        self.gregorian_calendar = ChristianHolidayGenerator()
        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,
            self._compute_labour_day_holiday,
            self._compute_madaraka_day_holiday,
            self._compute_mazingira_day_holiday,
            self._compute_mashujaa_day_holiday,
            self._compute_jamhuri_day_holiday,
            self._compute_christmas_day_holiday,
            self._compute_boxing_day_holiday,

            # Variable / movable / lunar
            self._compute_idd_ul_fitr_holiday,       # 1 Shawwal
            self._compute_eid_al_adha_holiday,       # 10 Dhu al-Hijjah
            self._compute_good_friday_holiday,       # Friday before Easter
            self._compute_easter_monday_holiday,     # Day after Easter Sunday
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

    def _compute_labour_day_holiday(self, year: int):
        """Labour Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labour Day"}

    def _compute_madaraka_day_holiday(self, year: int):
        """Madaraka Day — fixed date: June 1."""
        return {date(year, 6, 1): "Madaraka Day"}

    def _compute_mazingira_day_holiday(self, year: int):
        """Mazingira Day — fixed date: October 10."""
        return {date(year, 10, 10): "Mazingira Day"}

    def _compute_mashujaa_day_holiday(self, year: int):
        """Mashujaa Day — fixed date: October 20."""
        return {date(year, 10, 20): "Mashujaa Day"}

    def _compute_jamhuri_day_holiday(self, year: int):
        """Jamhuri Day — fixed date: December 12."""
        return {date(year, 12, 12): "Jamhuri Day"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_boxing_day_holiday(self, year: int):
        """Boxing Day — fixed date: December 26."""
        return {date(year, 12, 26): "Boxing Day"}

    # -------------------------------
    # Variable / movable / lunar
    # -------------------------------

    def _compute_idd_ul_fitr_holiday(self, year: int):
        """Idd ul-Fitr — Islamic lunar: 1 Shawwal (end of Ramadan)."""
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Idd ul-Fitr (Tentative Date)"}

    def _compute_eid_al_adha_holiday(self, year: int):
        """Eid al-Adha — Islamic lunar: 10 Dhu al-Hijjah."""
        return {self.islamic_calendar.compute_eid_al_adha(year): "Eid al-Adha (Tentative Date)"}

    def _compute_good_friday_holiday(self, year: int):
        """Good Friday — Friday before Easter Sunday (Christian movable feast)."""
        return {self.gregorian_calendar.compute_good_friday(year): "Good Friday"}

    def _compute_easter_monday_holiday(self, year: int):
        """Easter Monday — Monday after Easter Sunday (Christian movable feast)."""
        return {self.gregorian_calendar.compute_easter_monday(year): "Easter Monday"}
