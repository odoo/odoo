from datetime import date, timedelta
from typing import Dict

from ..calendars.islamic_calendar import IslamicHolidayGenerator
from ..calendars.location import Location


class Morocco:
    country_code = "MA"

    def __init__(self):
        # Morocco - Capital: Rabat
        self.location = Location(
            lat=34.0209,
            lon=-6.8416,
            tz=0.0,        # Base offset UTC+0 (special DST rules not reflected here)
            height_m=75.0,
            visibility_thresholds=None,
        )
        self.islamic_calendar = IslamicHolidayGenerator(self.location)
        self._public_holiday_computers = [
            # Fixed-date holidays
            self._compute_new_years_day_holiday,
            self._compute_independence_manifesto_day_holiday,
            self._compute_amazigh_new_year_holiday,
            self._compute_labour_day_holiday,
            self._compute_feast_of_the_throne_holiday,
            self._compute_oued_ed_dahab_day_holiday,
            self._compute_revolution_king_people_holiday,
            self._compute_youth_day_holiday,
            self._compute_green_march_day_holiday,
            self._compute_independence_day_holiday,

            # Variable / lunar / government-shifted
            self._compute_eid_al_fitr_day_holiday,               # 1 Shawwal
            self._compute_eid_al_fitr_next_day_holiday,          # day after Eid al-Fitr
            self._compute_eid_al_adha_day_holiday,               # 10 Dhu al-Hijjah
            self._compute_eid_al_adha_span_holidays,             # additional days after Eid al-Adha
            self._compute_hijra_new_year_holiday,                # 1 Muharram
            self._compute_mawlid_tentative_holiday,              # 12 Rabi' al-awwal (tentative)
            self._compute_mawlid_next_day_tentative_holiday,     # day after Mawlid (tentative)
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

    def _compute_independence_manifesto_day_holiday(self, year: int):
        """Anniversary of the Independence Manifesto — fixed date: January 11."""
        return {date(year, 1, 11): "Anniversary of the Independence Manifesto"}

    def _compute_amazigh_new_year_holiday(self, year: int):
        """Amazigh New Year (Yennayer) — fixed date in Morocco: January 14."""
        return {date(year, 1, 14): "Amazigh New Year"}

    def _compute_labour_day_holiday(self, year: int):
        """Labour Day / May Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labour Day/May Day"}

    def _compute_feast_of_the_throne_holiday(self, year: int):
        """Feast of the Throne — fixed date: July 30."""
        return {date(year, 7, 30): "Feast of the Throne"}

    def _compute_oued_ed_dahab_day_holiday(self, year: int):
        """Anniversary of the Recovery Oued Ed-Dahab — fixed date: August 14."""
        return {date(year, 8, 14): "Anniversary of the Recovery Oued Ed-Dahab"}

    def _compute_revolution_king_people_holiday(self, year: int):
        """Anniversary of the Revolution of the King and the People — fixed date: August 20."""
        return {date(year, 8, 20): "Anniversary of the Revolution of the King and the People"}

    def _compute_youth_day_holiday(self, year: int):
        """Youth Day — fixed date: August 21."""
        return {date(year, 8, 21): "Youth Day"}

    def _compute_green_march_day_holiday(self, year: int):
        """Anniversary of the Green March — fixed date: November 6."""
        return {date(year, 11, 6): "Anniversary of the Green March"}

    def _compute_independence_day_holiday(self, year: int):
        """Independence Day — fixed date: November 18."""
        return {date(year, 11, 18): "Independence Day"}

    # -------------------------------
    # Variable / lunar / government-shifted (stubs)
    # -------------------------------

    def _compute_eid_al_fitr_day_holiday(self, year: int):
        """Eid al-Fitr — Islamic lunar: 1 Shawwal (end of Ramadan). Government may announce exact date yearly."""
        return {self.islamic_calendar.compute_eid_al_fitr(year): "Eid al-Fitr (Tentative Date)"}

    def _compute_eid_al_fitr_next_day_holiday(self, year: int):
        """Eid al-Fitr Holiday — day after Eid al-Fitr; government-announced each year."""
        eid_al_fitr_date = self.islamic_calendar.compute_eid_al_fitr(year)
        return {eid_al_fitr_date + timedelta(days=1): "Eid al-Fitr Holiday (Tentative Date)"}

    def _compute_eid_al_adha_day_holiday(self, year: int):
        """Eid al-Adha — Islamic lunar: 10 Dhu al-Hijjah; observed nationwide."""
        return {self.islamic_calendar.compute_eid_al_adha(year): "Eid al-Adha (Tentative Date)"}

    def _compute_eid_al_adha_span_holidays(self, year: int):
        """Eid al-Adha Holidays — additional days following Eid al-Adha; government-announced each year."""
        eid_al_adha_date = self.islamic_calendar.compute_eid_al_adha(year)
        return {eid_al_adha_date + timedelta(days=1): "Eid al-Adha Holiday (Tentative Date)"}

    def _compute_hijra_new_year_holiday(self, year: int):
        """Hijra (Islamic) New Year — 1 Muharram (lunar; varies annually)."""
        return {self.islamic_calendar.compute_islamic_new_year(year): "Hijra (Islamic) New Year (Tentative Date)"}

    def _compute_mawlid_tentative_holiday(self, year: int):
        """Prophet Muhammad's Birthday (Mawlid) — 12 Rabi' al-awwal; often listed as tentative pending confirmation."""
        return {self.islamic_calendar.compute_mawlid(year): "Prophet's Birthday (Tentative Date)"}

    def _compute_mawlid_next_day_tentative_holiday(self, year: int):
        """Prophet Muhammad's Birthday Holiday — day after Mawlid; tentative and government-announced."""
        prophet_birthday_date = self.islamic_calendar.compute_mawlid(year)
        return {prophet_birthday_date: "Prophet's Birthday Holiday (Tentative Date)"}
