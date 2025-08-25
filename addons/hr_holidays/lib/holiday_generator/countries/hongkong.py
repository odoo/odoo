from datetime import date, timedelta
from typing import Dict

from ..calendars.chinese_calendar import ChineseHolidayGenerator
from ..calendars.gregorian_calendar import ChristianHolidayGenerator
from ..calendars.hindu_calendar import HinduCalendar
from ..calendars.location import Location


class HongKong:
    country_code = "HK"

    def __init__(self):
        hongkong_location = Location(
            lat=22.3193,    # degrees north
            lon=114.1694,   # degrees east
            tz=8.0,         # Hong Kong Time (UTC+8, no DST)
            height_m=35.0,   # Approx. elevation in meters
            visibility_thresholds=None,
        )
        self.gregorian_calendar = ChristianHolidayGenerator()
        self.hindu_calendar = HinduCalendar(hongkong_location)
        self.chinese_calendar = ChineseHolidayGenerator(hongkong_location)
        self._public_holiday_computers = [
            # Fixed dates
            self._compute_new_years_day_holiday,
            self._compute_labour_day_holiday,
            self._compute_hksar_establishment_day_holiday,
            self._compute_national_day_holiday,
            self._compute_christmas_day_holiday,
            self._compute_first_weekday_after_christmas_day_holiday,

            # Variable / lunar / movable feasts
            self._compute_lunar_new_year_holiday,
            self._compute_second_day_lunar_new_year_holiday,
            self._compute_chung_yeung_festival_holiday,
            self._compute_third_day_lunar_new_year_holiday,
            self._compute_tomb_sweeping_day_holiday,
            self._compute_good_friday_holiday,
            self._compute_holy_saturday_holiday,
            self._compute_easter_monday_holiday,
            self._compute_buddhas_birthday_holiday,
            self._compute_dragon_boat_festival_holiday,
            self._compute_day_after_mid_autumn_festival_holiday,
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

    def _compute_labour_day_holiday(self, year: int):
        """Labour Day — fixed date: May 1."""
        return {date(year, 5, 1): "Labour Day"}

    def _compute_hksar_establishment_day_holiday(self, year: int):
        """HKSAR Establishment Day — fixed date: July 1."""
        return {date(year, 7, 1): "Hong Kong Special Administrative Region Establishment Day"}

    def _compute_national_day_holiday(self, year: int):
        """National Day — fixed date: October 1."""
        return {date(year, 10, 1): "National Day"}

    def _compute_christmas_day_holiday(self, year: int):
        """Christmas Day — fixed date: December 25."""
        return {date(year, 12, 25): "Christmas Day"}

    def _compute_first_weekday_after_christmas_day_holiday(self, year: int):
        """First Weekday After Christmas Day — fixed date: December 26."""
        return {date(year, 12, 26): "First Weekday After Christmas Day"}

    # -------------------------------
    # Variable / lunar / movable feasts (return  , docstring only)
    # -------------------------------

    def _compute_lunar_new_year_holiday(self, year: int):
        """Lunar New Year's Day — 1st day of the 1st lunar month (Jan-Feb)."""
        return {self.chinese_calendar.compute_chinese_new_year(year): "Lunar New Year's Day"}

    def _compute_second_day_lunar_new_year_holiday(self, year: int):
        """Second Day of Lunar New Year — 2nd day of the 1st lunar month"""
        lunar_new_year = self.chinese_calendar.compute_chinese_new_year(year)
        return {lunar_new_year + timedelta(days=1): "Second Day of Lunar New Year"}

    def _compute_third_day_lunar_new_year_holiday(self, year: int):
        """Third Day of Lunar New Year — 3rd day of the 1st lunar month"""
        lunar_new_year = self.chinese_calendar.compute_chinese_new_year(year)
        return {lunar_new_year + timedelta(days=2): "Third Day of Lunar New Year"}

    def _compute_chung_yeung_festival_holiday(self, year: int):
        """Chung Yeung Festival — 9th day of 9th lunar month. Varies, not fixed Gregorian date."""
        return {self.chinese_calendar.compute_double_ninth(year): "Chung Yeung Festival"}

    def _compute_tomb_sweeping_day_holiday(self, year: int):
        """Tomb Sweeping Day (Ching Ming Festival) — around April 4 or 5. Varies each year."""
        return {self.chinese_calendar.compute_qingming(year): "Tomb Sweeping Day"}

    def _compute_good_friday_holiday(self, year: int):
        """Good Friday — Friday before Easter Sunday. Varies each year."""
        return {self.gregorian_calendar.compute_good_friday(year): "Good Friday"}

    def _compute_holy_saturday_holiday(self, year: int):
        """Holy Saturday — Day after Good Friday (Easter Saturday). Varies each year."""
        return {self.gregorian_calendar.compute_holy_saturday(year): "Holy Saturday"}

    def _compute_easter_monday_holiday(self, year: int):
        """Easter Monday — Day after Easter Sunday. Varies each year."""
        return {self.gregorian_calendar.compute_easter_monday(year): "Easter Monday"}

    def _compute_buddhas_birthday_holiday(self, year: int):
        """Buddha's Birthday — 8th day of the 4th lunar month. Varies each year (Apr-May)."""
        # It falls on the 8th day of the 4th lunar month.
        return {self.hindu_calendar._compute_buddha_purnima_holiday(year): "Buddha's Birthday"}

    def _compute_dragon_boat_festival_holiday(self, year: int):
        """Dragon Boat Festival — 5th day of the 5th lunar month. Varies each year (May-Jun)."""
        # 5th day of the 5th lunar month.
        return {self.chinese_calendar.compute_dragon_boat(year): "Dragon Boat Festival"}

    def _compute_day_after_mid_autumn_festival_holiday(self, year: int):
        """Day after Mid-Autumn Festival — 16th day of the 8th lunar month. Varies each year (Sep-Oct)."""
        # 15th day of the 8th lunar month,
        return {self.chinese_calendar.compute_mid_autumn(year) + timedelta(days=1): "Day after Mid-Autumn Festival"}
