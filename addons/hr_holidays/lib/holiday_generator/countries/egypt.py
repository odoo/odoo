from datetime import date, timedelta
from typing import Dict

from ..calendars.gregorian_calendar import ChristianHolidayGenerator
from ..calendars.utils.time_utils import first_weekday_on_or_after
from ..calendars.location import Location
from ..calendars.islamic_calendar import IslamicHolidayGenerator


class Egypt:
    country_code = "EG"

    def __init__(self):
        self.gregorian_calendar = ChristianHolidayGenerator()
        # Cairo, Egypt (UTC+2, no DST considered)
        egypt_location = Location(
            lat=30.0444,          # latitude north
            lon=31.2357,          # longitude east
            tz=2.0,               # UTC+2
            height_m=23.0,        # approx elevation in meters
            method="astronomical",
            visibility_thresholds=None,
        )
        self.islamic_calendar = IslamicHolidayGenerator(egypt_location)

        self._public_holiday_computers = [
            # Static dates
            self._compute_coptic_christmas_day_holiday,
            self._compute_revolution_day_january_25_holiday,
            self._compute_sinai_liberation_day_holiday,
            self._compute_labor_day_holiday,
            self._compute_june_30_revolution_holiday,
            self._compute_armed_forces_day_holiday,

            # Variable / religious or announced
            self._compute_spring_festival_holiday,           # Easter Monday (Sham El-Nessim)
            self._compute_day_off_for_revolution_day_january_25_holiday,
            self._compute_day_off_for_june_30_revolution,
            self._compute_day_off_for_revolution_day_jul23,
            self._compute_arafah_day_holiday,                # 9 Dhu al-Hijjah
            self._compute_eid_al_adha_holiday,               # 10 Dhu al-Hijjah
            self._compute_eid_al_adha_span_holidays,         # 2025-06-07..10
            self._compute_muharram_holiday,                  # Islamic New Year
            self._compute_mawlid_tentative_holiday,          # Prophet's Birthday
            self._compute_eid_al_fitr_holiday,               # 1 Shawwal
            self._compute_eid_al_fitr_span_holidays,
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
    # Static date holidays (implemented)
    # -------------------------------

    def _compute_coptic_christmas_day_holiday(self, year: int):
        return {date(year, 1, 7): "Coptic Christmas Day"}

    def _compute_revolution_day_january_25_holiday(self, year: int):
        return {date(year, 1, 25): "Revolution Day January 25"}

    def _compute_sinai_liberation_day_holiday(self, year: int):
        return {date(year, 4, 25): "Sinai Liberation Day"}

    def _compute_labor_day_holiday(self, year: int):
        return {date(year, 5, 1): "Labor Day"}

    def _compute_june_30_revolution_holiday(self, year: int):
        return {date(year, 6, 30): "June 30 Revolution"}

    def _compute_armed_forces_day_holiday(self, year: int):
        return {date(year, 10, 6): "Armed Forces Day"}

    # -------------------------------
    # Variable / announced holidays
    # -------------------------------

    def _compute_day_off_for_june_30_revolution(self, year: int) -> Dict[date, str]:
        """
            Government 'day off' adjustment for June 30 Revolution.
            Rule of thumb used in Egypt since 2020: shift many midweek holidays to Thursday.
            Here: choose the first Thursday on or after June 30.
        """
        base = date(year, 6, 30)
        th = first_weekday_on_or_after(base, weekday=3)  # Thursday=3
        return {th: "Day Off (June 30 Revolution)"}  # ad hoc; include if you want an 'always-thursday' policy

    def _compute_day_off_for_revolution_day_january_25_holiday(self, year: int) -> Dict[date, str]:
        """
            Government 'day off' adjustment for Revolution Day (January 25).
            Choose the first Thursday on or after Jan 25.
        """
        base = date(year, 1, 25)
        th = first_weekday_on_or_after(base, weekday=3)
        return {th: "Day Off (January 25 Revolution)"}

    def _compute_day_off_for_revolution_day_jul23(self, year: int) -> Dict[date, str]:
        """
            Government 'day off' adjustment for Revolution Day (July 23).
            Choose the first Thursday on or after Jul 23.
        """
        base = date(year, 7, 23)
        th = first_weekday_on_or_after(base, weekday=3)
        return {th: "Day Off (July 23 Revolution)"}

    def _compute_day_off_for_armed_forces_day(self, year: int) -> Dict[date, str]:
        """
            Government 'day off' adjustment for Armed Forces Day (Oct 6).
            Choose the first Thursday on or after Oct 6.
        """
        base = date(year, 10, 6)
        th = first_weekday_on_or_after(base, weekday=3)
        return {th: "Day Off (Armed Forces Day)"}

    def _compute_spring_festival_holiday(self, year: int):
        """Spring Festival (Sham El-Nessim): Monday after Coptic/Easter Sunday. Variable date each year."""
        # This is orthodox easter
        return {self.gregorian_calendar.compute_orthodox_easter_monday(year ): "Spring Festival (Sham El-Nessim)"}

    def _compute_eid_al_fitr_holiday(self, year: int):
        """Eid al-Fitr: 1 Shawwal in the Islamic calendar; lunar date, varies each year."""
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Eid al-Fitr (Tentative Date)"}

    def _compute_eid_al_fitr_span_holidays(self, year: int):
        """Eid al-Fitr Holiday span: government-declared extra days around Eid al-Fitr. Variable each year."""
        eid_date = self.islamic_calendar.compute_eid_al_fitr(year)
        eid_date_plus_1 = eid_date + timedelta(days=1)
        eid_date_plus_2 = eid_date + timedelta(days=2)
        eid_date_plus_3 = eid_date + timedelta(days=3)
        return {
            eid_date_plus_1: "Eid al-Fitr Holiday (Tentative Date)",
            eid_date_plus_2: "Eid al-Fitr Holiday (Tentative Date)",
            eid_date_plus_3: "Eid al-Fitr Holiday (Tentative Date)",
        }

    def _compute_arafah_day_holiday(self, year: int):
        """Arafah Day: 9 Dhu al-Hijjah (Islamic lunar calendar)."""
        return {self.islamic_calendar.compute_arafah(year): "Arafah Day (Tentative Date)"}

    def _compute_eid_al_adha_holiday(self, year: int):
        """Eid al-Adha: 10 Dhu al-Hijjah (Islamic lunar calendar)."""
        return {self.islamic_calendar.compute_eid_al_adha(year): "Eid al-Adha (Tentative Date)"}

    def _compute_eid_al_adha_span_holidays(self, year: int):
        """Eid al-Adha Holiday span: government-declared extra days around Eid al-Adha. Variable each year."""
        eid_al_adha_date = self.islamic_calendar.compute_eid_al_adha(year)
        eid_al_adha_date_plus_1 = eid_al_adha_date + timedelta(days=1)
        eid_al_adha_date_plus_2 = eid_al_adha_date + timedelta(days=2)
        eid_al_adha_date_plus_3 = eid_al_adha_date + timedelta(days=3)
        return {
            eid_al_adha_date_plus_1: "Eid al-Adha Holiday (Tentative Date)",
            eid_al_adha_date_plus_2: "Eid al-Adha Holiday (Tentative Date)",
            eid_al_adha_date_plus_3: "Eid al-Adha Holiday (Tentative Date)",
        }

    def _compute_muharram_holiday(self, year: int):
        """Islamic New Year (Hijri 1 Muharram). Lunar date, varies each year."""
        return {self.islamic_calendar.compute_islamic_new_year(year): "Muharram/New Year (Tentative Date)"}

    def _compute_mawlid_tentative_holiday(self, year: int):
        """Prophet Muhammad's Birthday (Mawlid an-Nabi): 12 Rabi' al-awwal (Islamic lunar calendar)."""
        return {self.islamic_calendar.compute_mawlid(year): "Prophet's Birthday (Tentative Date)"}
