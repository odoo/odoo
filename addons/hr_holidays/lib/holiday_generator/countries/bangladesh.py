from datetime import date, timedelta
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator
from ..calendars.hindu_calendar import HinduCalendar
from ..calendars.islamic_calendar import IslamicHolidayGenerator
from ..calendars.location import Location


class Bangladesh:
    country_code = "BD"

    def __init__(self):
        # Bangladesh - Capital: Dhaka
        dhaka_location = Location(
            lat=23.8103,
            lon=90.4125,
            tz=6.0,
            height_m=4.0,
            visibility_thresholds=None,
        )
        self.hindu_calendar = HinduCalendar(dhaka_location)
        self.gregorian_calendar = ChristianHolidayGenerator()
        self.islamic_calendar = IslamicHolidayGenerator(dhaka_location)

        self._public_holiday_computers = [
            # Static dates
            self._compute_language_martyrs_day_holiday,
            self._compute_independence_day_holiday,
            self._compute_bengali_new_year_holiday,
            self._compute_labor_day_holiday,
            self._compute_victory_day_holiday,

            # Variable / announced (stubs)
            self._compute_shab_e_barat_holiday,                  # lunar (Shaban 15)
            self._compute_shab_e_qadr_holiday,                   # odd nights of last 10 of Ramadan (govt announced)
            self._compute_eid_ul_fitr_holiday_days,              # govt-declared span around Eid al-Fitr
            self._compute_eid_ul_fitr_holiday,                   # Eid al-Fitr day (1 Shawwal)
            self._compute_buddha_purnima_vesak_holiday,          # Vaisakha Purnima
            self._compute_eid_al_adha_holiday_days,              # govt-declared span around Eid al-Adha
            self._compute_eid_al_adha_holiday,                   # Eid al-Adha day (10 Dhu al-Hijjah)
            self._compute_ashura_holiday,                        # 10 Muharram
            self._compute_student_people_uprising_day_holiday,   # usually 5 Aug (civic)
            self._compute_janmashtami_holiday,                   # Bhadrapada Krishna Ashtami
            self._compute_milad_un_nabi_tentative_holiday,       # 12 Rabi' al-awwal (tentative)
            self._compute_mahanabami_holiday,                    # Durga Puja period
            self._compute_durga_puja_holiday,                    # Durga Puja day
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
    # Static date holidays
    # -------------------------------

    def _compute_language_martyrs_day_holiday(self, year: int):
        return {date(year, 2, 21): "Language Martyrs' Day"}

    def _compute_independence_day_holiday(self, year: int):
        return {date(year, 3, 26): "Independence Day"}

    def _compute_bengali_new_year_holiday(self, year: int):
        return {date(year, 4, 14): "Bengali New Year"}

    def _compute_labor_day_holiday(self, year: int):
        return {date(year, 5, 1): "May Day"}

    def _compute_victory_day_holiday(self, year: int):
        return {date(year, 12, 16): "Victory Day"}

    # -------------------------------
    # Variable / announced holidays
    # -------------------------------


    def _compute_shab_e_barat_holiday(self, year: int):
        """Shab e-Barat — Islamic lunar: 15th night of Shaban (govt announced each year)."""
        return None

    def _compute_shab_e_qadr_holiday(self, year: int):
        """Shab-e-Qadr — Odd nights in last 10 days of Ramadan; official date announced yearly."""
        return None

    def _compute_eid_ul_fitr_holiday(self, year: int):
        """Eid ul-Fitr — Islamic lunar: 1 Shawwal (date varies by moon sighting)."""
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Eid ul-Fitr (Tentative Date)"}

    def _compute_eid_ul_fitr_holiday_days(self, year: int):
        """Eid ul-Fitr holiday span — multiple govt-declared days around 1 Shawwal."""
        eid_al_fitr_date = self.islamic_calendar.compute_eid_al_fitr(year)
        joint_eid_al_fitr_day1 = eid_al_fitr_date + timedelta(days=1)
        joint_eid_al_fitr_day2 = eid_al_fitr_date + timedelta(days=2)
        joint_eid_al_fitr_day3 = eid_al_fitr_date + timedelta(days=3)

        return {
            joint_eid_al_fitr_day1: "Eid ul-Fitr Holiday (Tentative Date)",
            joint_eid_al_fitr_day2: "Eid ul-Fitr Holiday (Tentative Date)",
            joint_eid_al_fitr_day3: "Eid ul-Fitr Holiday (Tentative Date)",
        }

    def _compute_buddha_purnima_vesak_holiday(self, year: int):
        """Buddha Purnima/Vesak — Vaisakha Purnima (lunar)."""
        return {self.hindu_calendar._compute_buddha_purnima_holiday(year): "Buddha Purnima/Vesak"}

    def _compute_eid_al_adha_holiday(self, year: int):
        """Eid al-Adha — Islamic lunar: 10 Dhu al-Hijjah (date varies by moon sighting)."""
        return {self.islamic_calendar.compute_eid_al_adha(year): "Eid al-Adha (Tentative Date)"}

    def _compute_eid_al_adha_holiday_days(self, year: int):
        """Eid al-Adha holiday span — multiple govt-declared days around 10 Dhu al-Hijjah."""
        eid_al_adha_date = self.islamic_calendar.compute_eid_al_adha(year)
        joint_eid_al_adha_day1 = eid_al_adha_date + timedelta(days=1)
        joint_eid_al_adha_day2 = eid_al_adha_date + timedelta(days=2)
        joint_eid_al_adha_day3 = eid_al_adha_date + timedelta(days=3)

        return {
            joint_eid_al_adha_day1: "Eid al-Adha Holiday (Tentative Date)",
            joint_eid_al_adha_day2: "Eid al-Adha Holiday (Tentative Date)",
            joint_eid_al_adha_day3: "Eid al-Adha Holiday (Tentative Date)",
        }

    def _compute_ashura_holiday(self, year: int):
        """Ashura — Islamic lunar: 10 Muharram."""
        return {self.islamic_calendar.compute_ashura(year): "Ashura (Tentative Date)"}

    def _compute_student_people_uprising_day_holiday(self, year: int):
        """Student-People Uprising Day — commonly observed on August 5."""
        return None

    def _compute_janmashtami_holiday(self, year: int):
        """Janmashtami — Bhadrapada Krishna Ashtami (Hindu lunisolar)."""
        return {self.hindu_calendar._compute_janmashtami_holiday(year): "Janmashtami"}

    def _compute_milad_un_nabi_tentative_holiday(self, year: int):
        """Eid e-Milad-un Nabi (Tentative) — 12 Rabi' al-awwal (Islamic lunar)."""
        return {self.islamic_calendar.compute_mawlid(year): "Eid e-Milad-un Nabi (Tentative Date)"}

    def _compute_mahanabami_holiday(self, year: int):
        """Mahanabami — during Durga Puja (Hindu lunisolar)."""
        return None

    def _compute_durga_puja_holiday(self, year: int):
        """Durga Puja — main day in the Puja period (Hindu lunisolar)."""
        return None
