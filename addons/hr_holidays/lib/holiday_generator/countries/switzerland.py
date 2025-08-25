from datetime import date
from typing import Dict


class Switzerland:
    country_code = "CH"

    def __init__(self):
        self._public_holiday_computers = [
            self._compute_swiss_national_day_holiday,   # 1 Aug
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
    # Nationwide holiday (every year)
    # -------------------------------

    def _compute_swiss_national_day_holiday(self, year: int):
        """Swiss National Day — fixed date: August 1 (National Holiday)."""
        return {date(year, 8, 1): "Swiss National Day"}
