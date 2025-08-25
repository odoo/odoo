from datetime import date, timedelta
from typing import Dict

from ..calendars.chinese_calendar import ChineseHolidayGenerator
from ..calendars.gregorian_calendar import ChristianHolidayGenerator
from ..calendars.hindu_calendar import HinduCalendar
from ..calendars.islamic_calendar import IslamicHolidayGenerator
from ..calendars.location import Location


class Indonesia:
    country_code = "ID"

    def __init__(self):
        jakarta_location = Location(
            lat=-6.2088,          # latitude south
            lon=106.8456,         # longitude east
            tz=7.0,               # UTC+7
            height_m=140.0,       # approx elevation in meters
            visibility_thresholds=None,
        )
        self.hindu_calendar = HinduCalendar(jakarta_location)
        self.gregorian_calendar = ChristianHolidayGenerator()
        self.chinese_calendar = ChineseHolidayGenerator(jakarta_location)
        self.islamic_calendar = IslamicHolidayGenerator(jakarta_location)
        self._public_holiday_computers = [
            # Fixed-date public holidays
            self._compute_new_years_day_holiday,
            self._compute_labour_day_holiday,
            self._compute_pancasila_day_holiday,
            self._compute_independence_day_holiday,
            self._compute_christmas_day_holiday,
            self._compute_boxing_day_holiday,

            # Variable / lunar / movable / govt-announced
            self._compute_ascension_of_prophet_holiday,         # Islamic (Isra Mi'raj) — variable
            self._compute_chinese_new_year_joint_holiday,       # Cuti Bersama — govt-announced
            self._compute_chinese_new_year_day_holiday,         # Lunar New Year — variable
            self._compute_nyepi_joint_holiday,                  # Cuti Bersama around Nyepi — govt-announced
            self._compute_nyepi_day_holiday,                    # Nyepi (Saka New Year) — variable
            self._compute_idul_fitri_day_holiday,               # 1 Shawwal — variable
            self._compute_idul_fitri_joint_holiday_span,        # Cuti Bersama around Idul Fitri — govt-announced
            self._compute_good_friday_holiday,                  # Friday before Easter — variable
            self._compute_easter_sunday_holiday,                # Easter Sunday — variable
            self._compute_waisak_day_holiday,                   # Buddha's Birthday — variable
            self._compute_waisak_joint_holiday,                 # Cuti Bersama around Waisak — govt-announced
            self._compute_ascension_day_of_jesus_holiday,       # Easter + 39 days — variable
            self._compute_ascension_day_joint_holiday,          # Cuti Bersama after Ascension — govt-announced
            self._compute_idul_adha_day_holiday,                # 10 Dhu al-Hijjah — variable
            self._compute_idul_adha_joint_holiday,              # Cuti Bersama after Idul Adha — govt-announced
            self._compute_muharram_islamic_new_year_holiday,    # 1 Muharram — variable
            self._compute_independence_day_observed_holiday,    # gov’t observed day (e.g., Mon if Sun) — ad hoc
            self._compute_maulid_nabi_tentative_holiday,        # 12 Rabi' al-awwal — variable (tentative)
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
    # Fixed-date public holidays (implemented every year)
    # -------------------------------

    def _compute_new_years_day_holiday(self, year: int):
        """New Year's Day — fixed date: January 1."""
        return {date(year, 1, 1): "New Year's Day"}

    def _compute_labour_day_holiday(self, year: int):
        """Labor Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labor Day"}

    def _compute_pancasila_day_holiday(self, year: int):
        """Pancasila Day — fixed date: June 1 (National Holiday)."""
        return {date(year, 6, 1): "Pancasila Day"}

    def _compute_independence_day_holiday(self, year: int):
        """Indonesian Independence Day — fixed date: August 17."""
        return {date(year, 8, 17): "Indonesian Independence Day"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_boxing_day_holiday(self, year: int):
        return {date(year, 12, 26): "Boxing Day"}

    # -------------------------------
    # Variable/lunar/movable/government-announced (docstring only; return None)
    # -------------------------------

    def _compute_chinese_new_year_day_holiday(self, year: int):
        """Chinese New Year's Day — 1st day of 1st lunar month; varies (Jan-Feb)."""
        return {self.chinese_calendar.compute_chinese_new_year(year): "Chinese New Year's Day"}

    def _compute_chinese_new_year_joint_holiday(self, year: int):
        """Chinese New Year Joint Holiday — Cuti Bersama decided by government each year."""
        chinese_new_year_day = self.chinese_calendar.compute_chinese_new_year(year)
        return {chinese_new_year_day + timedelta(days=1): "Chinese New Year Joint Holiday"}

    def _compute_nyepi_joint_holiday(self, year: int):
        """Joint Holiday for Bali's Day of Silence (Nyepi) — Cuti Bersama; announced annually."""
        return None

    def _compute_nyepi_day_holiday(self, year: int):
        """Bali's Day of Silence / Nyepi (Saka New Year) — Hindu lunisolar; variable date."""
        return None

    def _compute_ascension_of_prophet_holiday(self, year: int):
        """Ascension of the Prophet Muhammad (Isra Mi'raj) — Islamic lunars."""
        isra_date = self.islamic_calendar.compute_isra_miraj(year)
        if isra_date:
            return {isra_date: "Ascension of the Prophet Muhammad (Isra Mi'raj)"}
        return None

    def _compute_idul_fitri_day_holiday(self, year: int):
        """Idul Fitri (Eid al-Fitr) — Islamic lunar: 1 Shawwal; varies; govt sets public holidays around it."""
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Idul Fitri"}

    def _compute_idul_fitri_joint_holiday_span(self, year: int):
        """Idul Fitri Joint Holidays — Cuti Bersama span before/after Eid; announced annually."""
        eid_al_fitari_day = self.islamic_calendar.compute_eid_al_fitr(year)
        joint_eid_al_fitri_day1 = eid_al_fitari_day + timedelta(days=1)
        joint_eid_al_fitri_day2 = eid_al_fitari_day + timedelta(days=2)

        return {
            joint_eid_al_fitri_day1: "Idul Fitri Holiday",
            joint_eid_al_fitri_day2: "Idul Fitri Holiday",
        }

    def _compute_good_friday_holiday(self, year: int):
        """Good Friday — Friday before Easter; date varies by computus."""
        return {self.gregorian_calendar.compute_good_friday(year): "Good Friday"}

    def _compute_easter_sunday_holiday(self, year: int):
        """Easter Sunday — movable feast; date varies by computus."""
        return {self.gregorian_calendar.compute_easter_sunday(year): "Easter Sunday"}

    def _compute_waisak_day_holiday(self, year: int):
        """Waisak Day (Buddha's Anniversary) — Buddhist lunar calendar; date varies; govt announces."""
        return {self.hindu_calendar._compute_buddha_purnima_holiday(year): "Waisak Day"}

    def _compute_waisak_joint_holiday(self, year: int):
        """Joint Holiday for Waisak Day — Cuti Bersama; announced annually."""
        joint_budha_day = self.hindu_calendar._compute_buddha_purnima_holiday(year) + timedelta(days=1)
        return {joint_budha_day: "Waisak Joint Holiday"}

    def _compute_ascension_day_of_jesus_holiday(self, year: int):
        """Ascension Day of Jesus Christ — Easter + 39 days (Thursday); movable."""
        return {self.gregorian_calendar.compute_ascension(year): "Ascension Day of Jesus Christ"}

    def _compute_ascension_day_joint_holiday(self, year: int):
        """Joint Holiday after Ascension Day — Cuti Bersama; announced annually."""
        joint_ascension_day = self.gregorian_calendar.compute_ascension(year) + timedelta(days=1)
        return {joint_ascension_day: "Ascension Joint Holiday"}

    def _compute_idul_adha_day_holiday(self, year: int):
        """Idul Adha (Eid al-Adha) — Islamic lunar: 10 Dhu al-Hijjah; varies."""
        return {self.islamic_calendar.compute_eid_al_adha(year): "Idul Adha"}

    def _compute_idul_adha_joint_holiday(self, year: int):
        """Joint Holiday for Idul Adha — Cuti Bersama; announced annually."""
        eid_al_adha_day = self.islamic_calendar.compute_eid_al_adha(year)
        return {eid_al_adha_day + timedelta(days=1): "Idul Adha Joint Holiday"}

    def _compute_muharram_islamic_new_year_holiday(self, year: int):
        """Muharram / Islamic New Year — 1 Muharram (Hijri); lunar; varies."""
        return {self.islamic_calendar.compute_islamic_new_year(year): "Muharram / Islamic New Year"}

    def _compute_independence_day_observed_holiday(self, year: int):
        """Independence Day observed — government-observed weekday when Aug 17 falls on weekend (ad hoc)."""
        return None

    def _compute_maulid_nabi_tentative_holiday(self, year: int):
        """Maulid Nabi Muhammad (Prophet's Birthday) — 12 Rabi' al-awwal (Hijri); tentative each year."""
        return {self.islamic_calendar.compute_mawlid(year): "Maulid Nabi Muhammad (Tentative Date)"}
