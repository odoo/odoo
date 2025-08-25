from datetime import date, timedelta
from typing import Dict

from ..calendars.location import Location
from ..calendars.islamic_calendar import IslamicHolidayGenerator


class UnitedArabEmirates:
    country_code = "AE"

    def __init__(self):
        # Dubai, UAE (UTC+4, no DST considered)
        uae_location = Location(
            lat=25.276987,        # latitude north (Dubai)
            lon=55.296249,        # longitude east (Dubai)
            tz=4.0,               # UTC+4
            height_m=5.0,         # approx elevation in meters
            visibility_thresholds=(2.0, 8.0)  # minimum moon altitude above horizon and minimum sun-moon separation,
        )
        self.islamic_calendar = IslamicHolidayGenerator(uae_location)

        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,
            self._compute_national_day_holiday,
            self._compute_national_day_next_holiday,

            # Islamic lunar / government-announced
            self._compute_eid_al_fitr_day_holiday,     # 1 Shawwal
            self._compute_eid_al_fitr_span_holidays,   # extra days after Eid al-Fitr
            self._compute_arafat_day_holiday,          # 9 Dhu al-Hijjah
            self._compute_eid_al_adha_day_holiday,     # 10 Dhu al-Hijjah
            self._compute_eid_al_adha_span_holidays,   # extra days after Eid al-Adha
            self._compute_hijri_new_year_holiday,      # 1 Muharram
            self._compute_mouloud_tentative_holiday,   # 12 Rabi' al-awwal (tentative)
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

    def _compute_national_day_holiday(self, year: int):
        """National Day — fixed date: December 2."""
        return {date(year, 12, 2): "National Day"}

    def _compute_national_day_next_holiday(self, year: int):
        """National Day Holiday — fixed date: December 3 (adjacent public holiday)."""
        return {date(year, 12, 3): "National Day Holiday"}

    # -------------------------------
    # Islamic lunar / gov-announced
    # -------------------------------

    def _compute_eid_al_fitr_day_holiday(self, year: int):
        """
        Eid al-Fitr — Islamic lunar: 1 Shawwal (marks end of Ramadan).
        Public holiday; exact Gregorian date varies by moon-sighting.
        """
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Eid al-Fitr (Tentative)"}

    def _compute_eid_al_fitr_span_holidays(self, year: int):
        """
        Eid al-Fitr Holiday span — Government-declared additional days following Eid al-Fitr.
        Example 2025 list: multiple days Mar 31 – Apr 2.
        These are not fixed by Sharia, but by decree (e.g., UAE, KSA, Egypt).
        The span usually means:
        Day 1 = 1 Shawwalfrom ..calendars.location import Location
from ..calendars.islamic_calendar import IslamicHolidayGenerator (Eid day itself).
        Day 2+3 = extra public holidays (sometimes up to Day 4).
        Sometimes adjusted to align with weekends.
        """
        eid_day = self.islamic_calendar.compute_eid_al_fitr(year)
        span_days = 4  # default span for UAE usually 4–5 days. (Eid day + 3 extra days)
        return {eid_day + timedelta(span_days): "Eid al-Fitr Span (Tentative)"}

    def _compute_arafat_day_holiday(self, year: int):
        """
        Arafat (Hajj) Day — 9 Dhu al-Hijjah (day before Eid al-Adha).
        Islamic lunar; date varies annually.
        """
        return {self.islamic_calendar.compute_arafah(year): "Arafat (Tentative)"}

    def _compute_eid_al_adha_day_holiday(self, year: int):
        """
        Eid al-Adha (Feast of Sacrifice) — 10 Dhu al-Hijjah.
        Islamic lunar; date varies annually.
        """
        return {self.islamic_calendar.compute_eid_al_adha(year): "Eid al-Adha (Tentative)"}

    def _compute_eid_al_adha_span_holidays(self, year: int):
        """
        Eid al-Adha Holiday span — Government-declared extra days after Eid al-Adha.
        Example 2025 list: Jun 7–8.
        """
        eid_day = self.islamic_calendar.compute_eid_al_adha(year)
        span_days = 4  # default span for UAE usually 4–5 days. (Eid day + 3 extra days)

        return {eid_day + timedelta(days=span_days): "Eid al-Adha Span (Tentative)"}

    def _compute_hijri_new_year_holiday(self, year: int):
        """
        Al-Hijra (Islamic New Year) — 1 Muharram.
        Islamic lunar; date varies annually.
        """
        return {self.islamic_calendar.compute_islamic_new_year(year): "Al-Hijra (Tentative)"}

    def _compute_mouloud_tentative_holiday(self, year: int):
        """
        Mouloud (Prophet Muhammad's Birthday) — 12 Rabi' al-awwal.
        Often published as a tentative date pending official confirmation.
        """
        return {self.islamic_calendar.compute_mawlid(year): "Mouloud (Tentative)"}
