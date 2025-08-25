from datetime import date, timedelta
from typing import Dict

from ..calendars.islamic_calendar import IslamicHolidayGenerator
from ..calendars.location import Location


class Jordan:
    country_code = "JO"

    def __init__(self):
        # Location for Amman, Jordan (capital city)
        self.location = Location(
            lat=31.9454,     # degrees (north → positive)
            lon=35.9284,     # degrees (east → positive)
            tz=3.0,         # Jordan Standard Time (UTC+3, no DST since 2022)
            height_m=850.0,   # Approx. elevation in meters
            visibility_thresholds=None,
        )
        self.islamic_calendar = IslamicHolidayGenerator(self.location)
        self._public_holiday_computers = [
            # Fixed-date
            self._compute_new_years_day_holiday,
            self._compute_labour_day_holiday,
            self._compute_independence_day_holiday,
            self._compute_christmas_day_holiday,

            # Variable / lunar / government-announced
            self._compute_eid_al_fitr_day_holiday,       # 1 Shawwal
            self._compute_eid_al_fitr_holiday_span,      # govt-declared span after Eid al-Fitr
            self._compute_arafah_day_holiday,            # 9 Dhu al-Hijjah
            self._compute_eid_al_adha_day_holiday,       # 10 Dhu al-Hijjah
            self._compute_eid_al_adha_holiday_span,      # govt-declared span after Eid al-Adha
            self._compute_muharram_islamic_new_year,     # 1 Muharram
            self._compute_prophets_birthday_tentative,   # 12 Rabi' al-awwal
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
    # Fixed-date holidays (implemented)
    # -------------------------------

    def _compute_new_years_day_holiday(self, year: int):
        """New Year's Day — fixed date: January 1."""
        return {date(year, 1, 1): "New Year's Day"}

    def _compute_labour_day_holiday(self, year: int):
        """Labour Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labour Day"}

    def _compute_independence_day_holiday(self, year: int):
        """Independence Day — fixed date: May 25."""
        return {date(year, 5, 25): "Independence Day"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    # -------------------------------
    # Variable / lunar / government-announced (stubs)
    # -------------------------------

    def _compute_eid_al_fitr_day_holiday(self, year: int):
        """
        Eid al-Fitr — Islamic lunar: 1 Shawwal (marks end of Ramadan).
        Date varies each year (moon-sighting). Government may announce surrounding public holidays.
        """
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Eid al-Fitr (Tentative Date)"}

    def _compute_eid_al_fitr_holiday_span(self, year: int):
        """
        Eid al-Fitr Holiday span — Government-declared public holidays surrounding Eid al-Fitr.
        """
        eid_al_fitr_date = self.islamic_calendar.compute_eid_al_fitr(year)
        joint_eid_al_fitr_day1 = eid_al_fitr_date + timedelta(days=1)
        joint_eid_al_fitr_day2 = eid_al_fitr_date + timedelta(days=2)
        joint_eid_al_fitr_day3 = eid_al_fitr_date + timedelta(days=3)

        return {
            joint_eid_al_fitr_day1: "Eid al-Fitr Holiday (Tentative Date)",
            joint_eid_al_fitr_day2: "Eid al-Fitr Holiday (Tentative Date)",
            joint_eid_al_fitr_day3: "Eid al-Fitr Holiday (Tentative Date)",
        }

    def _compute_arafah_day_holiday(self, year: int):
        """
        Arafah Day — 9 Dhu al-Hijjah (day before Eid al-Adha).
        Islamic lunar date; varies annually by moon-sighting.
        """
        return {self.islamic_calendar.compute_arafah(year): "Arafah Day (Tentative Date)"}

    def _compute_eid_al_adha_day_holiday(self, year: int):
        """
        Eid al-Adha — 10 Dhu al-Hijjah.
        Islamic lunar date; varies annually by moon-sighting.
        """
        return {self.islamic_calendar.compute_eid_al_adha(year): "Eid al-Adha (Tentative Date)"}

    def _compute_eid_al_adha_holiday_span(self, year: int):
        """
        Eid al-Adha Holiday span — Government-declared additional public holidays
        """
        eid_al_adha_date = self.islamic_calendar.compute_eid_al_adha(year)
        joint_eid_al_adha_day1 = eid_al_adha_date + timedelta(days=1)
        joint_eid_al_adha_day2 = eid_al_adha_date + timedelta(days=2)
        joint_eid_al_adha_day3 = eid_al_adha_date + timedelta(days=3)

        return {
            joint_eid_al_adha_day1: "Eid al-Adha Holiday (Tentative Date)",
            joint_eid_al_adha_day2: "Eid al-Adha Holiday (Tentative Date)",
            joint_eid_al_adha_day3: "Eid al-Adha Holiday (Tentative Date)",
        }

    def _compute_muharram_islamic_new_year(self, year: int):
        """
        Muharram / Islamic New Year — 1 Muharram (Hijri).
        Islamic lunar date; varies annually by moon-sighting.
        """
        return {self.islamic_calendar.compute_islamic_new_year(year): "Islamic New Year (Tentative Date)"}

    def _compute_prophets_birthday_tentative(self, year: int):
        """
        Prophet's Birthday (Mawlid an-Nabi) — 12 Rabi' al-awwal.
        Often published as a tentative date pending official announcement.
        """
        return {self.islamic_calendar.compute_mawlid(year): "Prophet's Birthday (Tentative Date)"}
