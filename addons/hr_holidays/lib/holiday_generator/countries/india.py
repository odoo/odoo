from __future__ import annotations

from datetime import date
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator
from ..calendars.hindu_calendar import HinduCalendar
from ..calendars.islamic_calendar import IslamicHolidayGenerator
from ..calendars.location import Location


class India:
    country_code = "IN"

    def __init__(self):
        # Static location (New Delhi). Stateless across years.
        delhi_location = Location(
            lat=28.6139,          # latitude north
            lon=77.2090,          # longitude east
            tz=5.5,               # UTC+5:30
            height_m=216.0,       # approx elevation in meters
            method="astronomical",
            visibility_thresholds=None,
        )
        self.hindu_calendar = HinduCalendar(delhi_location)
        self.islamic_calendar = IslamicHolidayGenerator(delhi_location)
        self.gregorian_calendar = ChristianHolidayGenerator()

        # list of callables that take (year: int) -> Dict[date, str] | None
        self._public_holiday_computers = [
            self._compute_republic_day_holiday,
            self._compute_maha_shivaratri_holiday,
            self._compute_holi_holiday,
            self._compute_ramzan_id_holiday,
            self._compute_mahavir_jayanti_holiday,
            self._compute_good_friday_holiday,
            self._compute_buddha_purnima_holiday,
            self._compute_bakrid_holiday,
            self._compute_muharram_ashura_holiday,
            self._compute_independence_day_holiday,
            self._compute_janmashtami_holiday,
            self._compute_id_e_milad_holiday,
            self._compute_mahatma_gandhi_jayanti_holiday,
            self._compute_dussehra_holiday,
            self._compute_diwali_deepavali_holiday,
            self._compute_guru_nanak_jayanti_holiday,
            self._compute_christmas_holiday,
        ]

    # helper: get/create HinduCalendar for a year
    def _cal(self, year: int) -> HinduCalendar:
        hc = self._hc_by_year.get(year)
        if hc is None:
            hc = HinduCalendar(self.location)
            self._hc_by_year[year] = hc
        return hc

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
    # Fixed date holidays
    # -------------------------------
    def _compute_republic_day_holiday(self, year: int):
        if year >= 1950:
            return {date(year, 1, 26): "Republic Day"}
        return None

    def _compute_independence_day_holiday(self, year: int):
        return {date(year, 8, 15): "Independence Day"}

    def _compute_mahatma_gandhi_jayanti_holiday(self, year: int):
        return {date(year, 10, 2): "Mahatma Gandhi Jayanti"}

    def _compute_christmas_holiday(self, year: int):
        return {date(year, 12, 25): "Christmas"}

    # -------------------------------
    # Calculated (Hindu calendar) holidays
    # -------------------------------
    def _compute_maha_shivaratri_holiday(self, year: int):
        return {self.hindu_calendar._compute_maha_shivaratri(year): "Maha Shivaratri"}

    def _compute_holi_holiday(self, year: int):
        return {self.hindu_calendar._compute_holi(year): "Holi"}

    def _compute_mahavir_jayanti_holiday(self, year: int):
        return {self.hindu_calendar._compute_mahavir_jayanti_holiday(year): "Mahavir Jayanti"}

    def _compute_good_friday_holiday(self, year: int):
        return {self.gregorian_calendar.compute_good_friday(year): "Good Friday"}

    def _compute_buddha_purnima_holiday(self, year: int):
        return {self.hindu_calendar._compute_buddha_purnima_holiday(year): "Buddha Purnima"}

    def _compute_janmashtami_holiday(self, year: int):
        return {self.hindu_calendar._compute_janmashtami_holiday(year): "Janmashtami"}

    def _compute_dussehra_holiday(self, year: int):
        return {self.hindu_calendar._compute_dussehra_holiday(year): "Dussehra"}

    def _compute_diwali_deepavali_holiday(self, year: int):
        return {self.hindu_calendar._compute_diwali(year): "Diwali"}

    def _compute_guru_nanak_jayanti_holiday(self, year: int):
        return {self.hindu_calendar._compute_guru_nanak_jayanti_holiday(year): "Guru Nanak Jayanti"}

    # -------------------------------
    # Islamic (lunar) holidays - stubs
    # -------------------------------
    def _compute_id_e_milad_holiday(self, year: int):
        return {self.islamic_calendar.compute_mawlid(year): "Id-e-Milad (Tentative Date)"}

    def _compute_ramzan_id_holiday(self, year: int):
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Ramzan Id (Tentative Date)"}

    def _compute_bakrid_holiday(self, year: int):
        return {self.islamic_calendar.compute_eid_al_adha(year): "Bakrid (Tentative Date)"}

    def _compute_muharram_ashura_holiday(self, year: int):
        return {self.islamic_calendar.compute_ashura(year): "Muharram/Ashura (Tentative Date)"}
