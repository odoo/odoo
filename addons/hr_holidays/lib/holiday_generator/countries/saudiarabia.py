from datetime import date, timedelta
from typing import Dict

from ..calendars.location import Location
from ..calendars.islamic_calendar import IslamicHolidayGenerator


class SaudiArabia:
    country_code = "SA"

    def __init__(self):
        # Riyadh, Saudi Arabia (UTC+3, no DST considered)
        saudi_location = Location(
            lat=24.7136,          # latitude north
            lon=46.6753,          # longitude east
            tz=3.0,               # UTC+3
            height_m=600.0,       # approx elevation in meters
            visibility_thresholds=(2.0, 8.0) # minimum moon altitude above horizon and minimum sun-moon separation
        )
        self.islamic_calendar = IslamicHolidayGenerator(saudi_location)

        self._public_holiday_computers = [
            # Fixed-date holiday
            self._compute_founding_day_holiday,

            # Variable / Islamic lunar holidays
            self._compute_eid_al_fitr_day_holiday,        # 1 Shawwal
            self._compute_eid_al_fitr_holiday_span,       # extra days after Eid al-Fitr
            self._compute_arafat_day_holiday,             # 9 Dhu al-Hijjah
            self._compute_eid_al_adha_day_holiday,        # 10 Dhu al-Hijjah
            self._compute_eid_al_adha_holiday_span,       # extra days after Eid al-Adha
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
    # Fixed-date holiday (every year)
    # -------------------------------

    def _compute_founding_day_holiday(self, year: int):
        """Founding Day — fixed date: February 22."""
        return {date(year, 2, 22): "Founding Day"}

    # -------------------------------
    # Islamic lunar holidays
    # -------------------------------

    def _compute_eid_al_fitr_day_holiday(self, year: int):
        """
        Eid al-Fitr — Islamic lunar: 1 Shawwal (end of Ramadan).
        Varies annually by moon-sighting; multiple days are given as public holidays.
        """
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Eid al-Fitr (Tentative)"}

    def _compute_eid_al_fitr_holiday_span(self, year: int):
        """
        Eid al-Fitr Holiday span — Government-declared extra days following Eid al-Fitr.
        Example 2025: 31 Mar – 2 Apr.
        """
        eid_day = self.islamic_calendar.compute_eid_al_fitr(year)
        span_days = 3  # default span for Saudi Arabia usually 3 days. (Eid day + 3 extra days)
        return {eid_day + timedelta(span_days): "Eid al-Fitr Span (Tentative)"}

    def _compute_arafat_day_holiday(self, year: int):
        """
        Arafat Day — 9 Dhu al-Hijjah, day before Eid al-Adha.
        Varies annually by Islamic lunar calendar.
        """
        return {self.islamic_calendar.compute_arafah(year): "Arafat (Tentative)"}

    def _compute_eid_al_adha_day_holiday(self, year: int):
        """
        Eid al-Adha — Islamic lunar: 10 Dhu al-Hijjah.
        Major Islamic festival; varies annually by moon-sighting.
        """
        return {self.islamic_calendar.compute_eid_al_adha(year): "Eid al-Adha (Tentative)"}

    def _compute_eid_al_adha_holiday_span(self, year: int):
        """
        Eid al-Adha Holiday span — Government-declared additional days following Eid al-Adha.
        Example 2025: 7–8 Jun.
        """
        eid_day = self.islamic_calendar.compute_eid_al_fitr(year)
        span_days = 3  # default span for Saudi Arabia usually 3 days. (Eid day + 3 extra days)
        return {eid_day + timedelta(span_days): "Eid al-Adha Span (Tentative)"}
