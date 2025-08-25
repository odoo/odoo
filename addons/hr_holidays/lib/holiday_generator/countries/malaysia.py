from datetime import date, timedelta
from typing import Dict

from ..calendars.chinese_calendar import ChineseHolidayGenerator
from ..calendars.hindu_calendar import HinduCalendar
from ..calendars.islamic_calendar import IslamicHolidayGenerator
from ..calendars.location import Location


class Malaysia:
    country_code = "MY"

    def __init__(self):
        # Malaysia - Capital: Kuala Lumpur
        kaula_location = Location(
            lat=3.1390,
            lon=101.6869,
            tz=8.0,
            height_m=56.0,
            visibility_thresholds=None,
        )
        self.hindu_calendar = HinduCalendar(kaula_location)
        self.chinese_calendar = ChineseHolidayGenerator(kaula_location)
        self.islamic_calendar = IslamicHolidayGenerator(kaula_location)
        self._public_holiday_computers = [
            # Fixed-date federal holidays
            self._compute_labour_day_holiday,
            self._compute_malaysia_national_day,
            self._compute_malaysia_day,
            self._compute_christmas_day_holiday,

            # Variable / lunar / government-set
            self._compute_chinese_new_year_day,         # Lunar New Year (Day 1)
            self._compute_chinese_new_year_day2,        # Lunar New Year (Day 2)
            self._compute_hari_raya_puasa,              # Eid al-Fitr (Hari Raya Aidilfitri) Day 1
            self._compute_hari_raya_puasa_day2,         # Eid al-Fitr Day 2
            self._compute_wesak_day,                    # Buddha's Birthday (Vesak)
            self._compute_agongs_birthday,              # Yang di-Pertuan Agong's Birthday
            self._compute_hari_raya_haji,               # Eid al-Adha (Hari Raya Haji) Day 1
            self._compute_hari_raya_haji_day2,          # Eid al-Adha Day 2
            self._compute_muharram_islamic_new_year,    # 1 Muharram
            self._compute_prophets_birthday_tentative,  # 12 Rabi' al-awwal (Mawlid) (tentative)
            self._compute_malaysia_day_observed,        # Malaysia Day Holiday (observed)
            self._compute_diwali_deepavali,             # Deepavali
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
    # Fixed-date federal holidays (implemented)
    # -------------------------------

    def _compute_labour_day_holiday(self, year: int):
        """Labour Day — fixed date: May 1 (Federal Public Holiday)."""
        return {date(year, 5, 1): "Labour Day"}

    def _compute_malaysia_national_day(self, year: int):
        """Malaysia's National Day (Hari Merdeka) — fixed date: August 31."""
        return {date(year, 8, 31): "Malaysia's National Day"}

    def _compute_malaysia_day(self, year: int):
        """Malaysia Day — fixed date: September 16."""
        return {date(year, 9, 16): "Malaysia Day"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    # -------------------------------
    # Variable / lunar / government-set
    # -------------------------------

    def _compute_chinese_new_year_day(self, year: int):
        """Chinese New Year's Day — 1st day of the 1st lunar month"""
        return {self.chinese_calendar.compute_chinese_new_year(year): "Chinese New Year's Day"}

    def _compute_chinese_new_year_day2(self, year: int):
        """Second Day of Chinese New Year — 2nd day of the 1st lunar month"""
        new_year_day = self.chinese_calendar.compute_chinese_new_year(year)
        return {new_year_day + timedelta(days=1): "Second Day of Chinese New Year"}

    def _compute_hari_raya_puasa(self, year: int):
        """Hari Raya Puasa (Eid al-Fitr) — 1 Shawwal (Islamic lunar; varies; Federal Public Holiday)."""
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Hari Raya Puasa (Tentative Date)"}

    def _compute_hari_raya_puasa_day2(self, year: int):
        """Hari Raya Puasa Day 2 — government-set second day following Eid al-Fitr (varies)."""
        hari_raya_date = self.islamic_calendar.compute_eid_al_fitr(year)
        return {hari_raya_date + timedelta(days=1): "Hari Raya Puasa Day 2 (Tentative Date)"}

    def _compute_wesak_day(self, year: int):
        """Wesak Day (Buddha's Anniversary) — Buddhist lunar calendar; government announces date annually."""
        return {self.hindu_calendar._compute_buddha_purnima_holiday(year): "Wesak Day"}

    def _compute_agongs_birthday(self, year: int):
        """The Yang di-Pertuan Agong's Birthday — date is set by government and may change by reign/year."""
        return None

    def _compute_hari_raya_haji(self, year: int):
        """Hari Raya Haji (Eid al-Adha) — 10 Dhu al-Hijjah (Islamic lunar; varies)."""
        return {self.islamic_calendar.compute_eid_al_adha(year): "Hari Raya Haji (Tentative Date)"}

    def _compute_hari_raya_haji_day2(self, year: int):
        """Hari Raya Haji (Day 2) — government-set additional day after Eid al-Adha (varies)."""
        hari_raya_haji_date = self.islamic_calendar.compute_eid_al_adha(year)
        return {hari_raya_haji_date + timedelta(days=1): "Hari Raya Haji Day 2 (Tentative Date)"}

    def _compute_muharram_islamic_new_year(self, year: int):
        """Muharram / Islamic New Year — 1 Muharram (Islamic lunar; varies)."""
        return {self.islamic_calendar.compute_islamic_new_year(year): "Muharram / Islamic New Year (Tentative Date)"}

    def _compute_prophets_birthday_tentative(self, year: int):
        """The Prophet Muhammad's Birthday (Mawlid) — 12 Rabi' al-awwal; often published as tentative."""
        return {self.islamic_calendar.compute_mawlid(year): "Prophet's Birthday (Tentative Date)"}

    def _compute_malaysia_day_observed(self, year: int):
        """Malaysia Day Holiday — observed/adjacent holiday when Malaysia Day falls near a weekend"""
        return None

    def _compute_diwali_deepavali(self, year: int):
        """Diwali / Deepavali — Hindu lunisolar calendar; varies by year and state observance."""
        return {self.hindu_calendar._compute_diwali(year): "Diwali / Deepavali"}
