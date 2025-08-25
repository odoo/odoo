from datetime import date, timedelta
from typing import Dict

from ..calendars.location import Location
from ..calendars.islamic_calendar import IslamicHolidayGenerator


class Pakistan:
    country_code = "PK"

    def __init__(self):
        # Islamabad, Pakistan (UTC+5, no DST considered)
        pakistan_location = Location(
            lat=33.6844,          # latitude north
            lon=73.0479,          # longitude east
            tz=5.0,               # UTC+5
            height_m=540.0,       # approx elevation in meters
            visibility_thresholds=(2.0, 8.0),  # (altitude_deg, elongation_deg)
        )
        self.islamic_calendar = IslamicHolidayGenerator(pakistan_location)

        self._public_holiday_computers = [
            # Fixed-date holidays (implemented)
            self._compute_kashmir_day_holiday,
            self._compute_pakistan_day_holiday,
            self._compute_labour_day_holiday,
            self._compute_youm_i_takbeer_holiday,
            self._compute_independence_day_holiday,
            self._compute_iqbal_day_holiday,
            self._compute_christmas_day_holiday,
            self._compute_quaid_e_azam_day_holiday,

            # Variable / lunar / government-announced
            self._compute_eid_ul_fitr_day_holiday,      # 1 Shawwal
            self._compute_eid_ul_fitr_holiday_span,     # govt-declared extra days after Eid-ul-Fitr
            self._compute_chand_raat_holiday,           # eve holiday (govt-announced)
            self._compute_eid_al_adha_day_holiday,      # 10 Dhu al-Hijjah
            self._compute_eid_al_adha_holiday_span,     # govt-declared extra days after Eid al-Adha
            self._compute_ashura_day_holiday,           # 10 Muharram
            self._compute_ashura_holiday_span,          # 9–10 Muharram days
            self._compute_eid_milad_un_nabi_tentative,  # 12 Rabi' al-awwal (tentative)
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

    def _compute_kashmir_day_holiday(self, year: int):
        """Kashmir Day — fixed date: February 5."""
        return {date(year, 2, 5): "Kashmir Day"}

    def _compute_pakistan_day_holiday(self, year: int):
        """Pakistan Day — fixed date: March 23."""
        return {date(year, 3, 23): "Pakistan Day"}

    def _compute_labour_day_holiday(self, year: int):
        """Labour Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labour Day"}

    def _compute_youm_i_takbeer_holiday(self, year: int):
        """Youm-i-Takbeer — fixed date as listed: May 28."""
        return {date(year, 5, 28): "Youm-i-Takbeer"}

    def _compute_independence_day_holiday(self, year: int):
        """Independence Day — fixed date: August 14."""
        return {date(year, 8, 14): "Independence Day"}

    def _compute_iqbal_day_holiday(self, year: int):
        """Iqbal Day — fixed date: November 9."""
        return {date(year, 11, 9): "Iqbal Day"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_quaid_e_azam_day_holiday(self, year: int):
        """Quaid-e-Azam Day — fixed date: December 25 (same date as Christmas Day)."""
        return {date(year, 12, 25): "Quaid-e-Azam Day"}

    # -------------------------------
    # Variable / lunar / government-announced (stubs)
    # -------------------------------

    def _compute_eid_ul_fitr_day_holiday(self, year: int):
        """
        Eid-ul-Fitr — Islamic lunar: 1 Shawwal (end of Ramadan).
        Date varies annually by moon-sighting; government may also declare adjacent holidays.
        """
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Eid ul-Fitr (Tentative)"}

    def _compute_eid_ul_fitr_holiday_span(self, year: int):
        """
        Eid-ul-Fitr Holiday span — Government-declared additional public holidays
        around the Eid-ul-Fitr day (e.g., +1 to +2 days).
        """
        eid_day = self.islamic_calendar.compute_eid_al_fitr(year)
        span_days = 3  # Eid day + 2 days more

        return {eid_day + timedelta(span_days): "Eid al-Fitr Span (Tentative)"}

    def _compute_chand_raat_holiday(self, year: int):
        """
        Chand Raat Holiday — Eve before a major Islamic festival (often Eid).
        Government-announced ad hoc; not fixed annually.
        """
        eid_day = self.islamic_calendar.compute_eid_al_fitr(year)
        chand_raat = eid_day - timedelta(days=1)

        return {chand_raat: "Chand Raat (Tentative)"}

    def _compute_eid_al_adha_day_holiday(self, year: int):
        """
        Eid al-Adha — Islamic lunar: 10 Dhu al-Hijjah.
        Date varies annually by moon-sighting.
        """
        return {self.islamic_calendar.compute_eid_al_adha(year): "Eid al-Fitr (Tentative)"}

    def _compute_eid_al_adha_holiday_span(self, year: int):
        """
        Eid al-Adha Holiday span — Government-declared additional public holidays
        following Eid al-Adha (e.g., +1 to +3 days).
        """
        eid_day = self.islamic_calendar.compute_eid_al_adha(year)
        span_days = 4  # Eid day + 3 more

        return {eid_day + timedelta(days=span_days): "Eid al-Adha (Tentative)"}

    def _compute_ashura_day_holiday(self, year: int):
        """
        Ashura — 10 Muharram (Islamic lunar).
        Public holiday date varies annually; often observed with adjacent day(s).
        """
        return {self.islamic_calendar.compute_ashura(year): "Ashura (Tentative)"}

    def _compute_ashura_holiday_span(self, year: int):
        """
        Ashura Holiday span — Additional day(s) around 9-10 Muharram as announced by government.
        """
        ashura_day = self.islamic_calendar.compute_ashura(year)
        span_days = 2  # 9th and 10th Muharram

        return {ashura_day - timedelta(days=span_days): "Ashura Span (Tentative)"}

    def _compute_eid_milad_un_nabi_tentative(self, year: int):
        """
        Eid Milad un-Nabi (Prophet Muhammad's Birthday) — 12 Rabi' al-awwal.
        Often listed as tentative pending official announcement each year.
        """
        return {self.islamic_calendar.compute_mawlid(year): "Eid Milad un-Nabi (Tentative)"}
