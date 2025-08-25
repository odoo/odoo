from datetime import date
from typing import Dict, Iterable

from . import countries


class HolidayGenerator:
    def __init__(self):
        self._instances = {}

    def _get_country(self, country_code: str):
        code = country_code.upper()
        if code in self._instances:
            return self._instances[code]

        try:
            _ = countries.COUNTRY_CLASS_MAP[code]
        except KeyError:
            raise ValueError(f"Unsupported country code: {country_code!r}")

        # Lazy-load class via countries.__getattr__
        cls = getattr(countries, code)
        inst = cls()
        self._instances[code] = inst
        return inst

    def generate(self, country_code: str, years: int | Iterable[int]) -> Dict[date, str]:
        """
        Return a merged Dict[date, str] for the given year(s).
        If multiple holidays fall on the same date across years,
        merge the names with '; '.
        """
        year_list = [years] if isinstance(years, int) else list(years)
        country = self._get_country(country_code)

        merged: Dict[date, str] = {}
        for year in year_list:
            year_map = country.holidays_for_year(year)
            for d, name in year_map.items():
                if d in merged:
                    merged[d] = f"{merged[d]}; {name}"
                else:
                    merged[d] = name
        return dict(sorted(merged.items(), key=lambda x: (x[0], x[1])))
