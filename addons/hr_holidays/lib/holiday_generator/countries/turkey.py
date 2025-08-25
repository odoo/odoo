from datetime import date,timedelta
from typing import Dict

from ..calendars.location import Location
from ..calendars.islamic_calendar import IslamicHolidayGenerator

class Turkey:
    country_code = "TR"

    def __init__(self):
        # Istanbul, Turkey (UTC+3, no DST considered)
        turkey_location = Location(
            lat=41.0082,          # latitude north
            lon=28.9784,          # longitude east
            tz=3.0,               # UTC+3
            height_m=40.0,        # approx elevation in meters
            visibility_thresholds=(2.0, 8.0) # minimum moon altitude above horizon and minimum sun-moon separation
        )
        self.islamic_calendar = IslamicHolidayGenerator(turkey_location)

        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,
            self._compute_national_sovereignty_childrens_day,
            self._compute_labor_and_solidarity_day,
            self._compute_commemoration_ataturk_youth_sports,
            self._compute_democracy_national_unity_day,
            self._compute_victory_day_holiday,
            self._compute_republic_day_holiday,

            # Variable / Islamic lunar
            self._compute_ramadan_feast_day,                     # Eid al-Fitr (Şeker Bayramı) – day 1
            self._compute_ramadan_feast_holiday_span,            # extra/other Ramadan Feast days
            self._compute_sacrifice_feast_day,                   # Eid al-Adha (Kurban Bayramı) – day 1
            self._compute_sacrifice_feast_holiday_span,          # extra Sacrifice Feast holidays
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
    # Fixed-date holidays
    # -------------------------------

    def _compute_new_years_day_holiday(self, year: int):
        """New Year's Day — fixed date: January 1."""
        return {date(year, 1, 1): "New Year's Day"}

    def _compute_national_sovereignty_childrens_day(self, year: int):
        """National Sovereignty and Children's Day — fixed date: April 23."""
        return {date(year, 4, 23): "National Sovereignty and Children's Day"}

    def _compute_labor_and_solidarity_day(self, year: int):
        """Labor and Solidarity Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labor and Solidarity Day"}

    def _compute_commemoration_ataturk_youth_sports(self, year: int):
        """Commemoration of Atatürk, Youth and Sports Day — fixed date: May 19."""
        return {date(year, 5, 19): "Commemoration of Atatürk, Youth and Sports Day"}

    def _compute_democracy_national_unity_day(self, year: int):
        """Democracy and National Unity Day — fixed date: July 15."""
        return {date(year, 7, 15): "Democracy and National Unity Day"}

    def _compute_victory_day_holiday(self, year: int):
        """Victory Day — fixed date: August 30."""
        return {date(year, 8, 30): "Victory Day"}

    def _compute_republic_day_holiday(self, year: int):
        """Republic Day — fixed date: October 29."""
        return {date(year, 10, 29): "Republic Day"}

    # -------------------------------
    # Variable / Islamic lunar
    # -------------------------------

    def _compute_ramadan_feast_day(self, year: int):
        """
        Ramadan Feast (Eid al-Fitr / Şeker Bayram) — Islamic lunar: 1 Shawwal.
        In practice Turkey observes multiple consecutive days for the feast; dates vary annually by moon-sighting.
        """
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Eid al-Fitr (Tentative)"}

    def _compute_ramadan_feast_holiday_span(self, year: int):
        """
        Ramadan Feast Holiday span — additional/adjacent public holidays around Eid al-Fitr,
        often covering 2-5 days as published by the government each year.
        """
        eid_day = self.islamic_calendar.compute_eid_al_fitr(year)
        span_days = 3  # default span for Turkey usually 3 days. (Eid day + 2 extra days)
        return {eid_day + timedelta(span_days): "Eid al-Fitr Span (Tentative)"}


    def _compute_sacrifice_feast_day(self, year: int):
        """
        Sacrifice Feast (Eid al-Adha / Kurban Bayram) — Islamic lunar: 10 Dhu al-Hijjah.
        Turkey typically observes a multi-day period; exact dates vary annually.
        """

        return {self.islamic_calendar.compute_eid_al_adha(year): "Eid al-Adha (Tentative)"}

    def _compute_sacrifice_feast_holiday_span(self, year: int):
        """
        Sacrifice Feast Holiday span — additional public holidays around Eid al-Adha,
        commonly 3-4 extra days, announced each year by the government.
        """
        eid_day = self.islamic_calendar.compute_eid_al_adha(year)
        span_days = 3  # default span for Turkey usually 3 days. (Eid day + 2 extra days)
        return {eid_day + timedelta(span_days): "Eid al-Adha Span (Tentative)"}
