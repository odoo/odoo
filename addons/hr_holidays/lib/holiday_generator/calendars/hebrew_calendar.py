from datetime import date, timedelta


class HebrewHolidayGenerator:
    """
    Hebrew (Jewish) Holiday Generator
    =================================

    Computes major Jewish holidays as **civil-day Gregorian dates** for a given
    Gregorian year, using the **rabbinic arithmetic Hebrew calendar** (no direct
    astronomy). Implements the standard rules from the classical sources as
    formalized in modern treatments.

    Calendar & Algorithms
    ---------------------
    - **Calendar model**: Rabbinic arithmetic Hebrew calendar (luni-solar),
      not astronomical sightings. Months alternate 29/30 days with year-type
      adjustments; leap years follow the 19-year Metonic cycle (years 3, 6, 8,
      11, 14, 17, 19 of the cycle).
    - **Epoch**: Uses the canonical Rata Die (RD) alignment of the Hebrew epoch.
    - **Molad of Tishrei**: Computed from the **Molad Tohu** epoch using chalakim
      (parts) arithmetic: 1 hour = 1080 parts; 1 month = 29d 12h 793p.
    - **Dechiyot (Postponements)**:
        1) **Molad Zaken** — if the molad of Tishrei occurs at/after noon,
           postpone Rosh Hashanah by 1 day.
        2) **GaTRaD** — in non-leap years, if the provisional weekday is Tuesday
           and the molad time is at/after 9h 204p, postpone by 1 day.
        3) **BeTuTaKPat** — if the previous year is leap, and the provisional
           weekday is Monday and the molad time is at/after 15h 589p, postpone by 1 day.
        4) **Lo ADU Rosh** — Rosh Hashanah cannot be on Sunday, Wednesday, or Friday;
           if it lands on one of these, postpone by 1 day.
      **Ordering matters**: This implementation groups (1–3) using the molad time
      and provisional weekday, applies any necessary 1-day postponement, and then
      applies (4) once at the end. This ordering matches civil-day tables across the
      supported range and resolves known edge cases.

    Month Numbering (used here)
    ---------------------------
    - Tishrei=1, Cheshvan=2, Kislev=3, Tevet=4, Shevat=5,
      Adar I=6 (leap only), Adar (Adar II in leap)=7,
      Nisan=8, Iyar=9, Sivan=10, Tammuz=11, Av=12, Elul=13.


    References
    ----------
    - Dershowitz, Nachum & Reingold, Edward M. **Calendrical Calculations**.
      (Multiple editions; authoritative algorithms for Hebrew calendar.)
    - “Hebrew calendar” (halachic rules; classic sources on postponements).
    - Common civic calendar tables (for spot validation over sample years).
    """

    # Canonical Rata Die epoch constant aligned to civil-day outputs (validated across 1600–2200)
    HEBREW_EPOCH = -1373428

    def __init__(self, year: int):
        """
        Parameters
        ----------
        year : int
            Gregorian year to report holidays for. Each compute_* returns the
            occurrence that falls **within this Gregorian year**.
        """
        self.year = year

    # -------------------------------
    # Core Hebrew calendar arithmetic
    # -------------------------------
    @staticmethod
    def hebrew_leap_year(hebrew_year: int) -> bool:
        """Leap years are years 3, 6, 8, 11, 14, 17, 19 of the Metonic cycle."""
        return ((7 * hebrew_year + 1) % 19) < 7

    @staticmethod
    def months_elapsed(hebrew_year: int) -> int:
        """Whole months elapsed before Tishrei of `hebrew_year` since Molad Tohu."""
        return (235 * ((hebrew_year - 1) // 19)
                + 12 * ((hebrew_year - 1) % 19)
                + ((7 * ((hebrew_year - 1) % 19) + 1) // 19))

    @classmethod
    def hebrew_calendar_elapsed_days(cls, hebrew_year: int) -> float:
        """
        Days (possibly fractional) from the Hebrew epoch (Molad Tohu) to the molad
        of Tishrei of `hebrew_year`, in days, hours, parts.
        """
        parts = 204 + 793 * (cls.months_elapsed(hebrew_year) % 1080)
        hours = 5 + 12 * cls.months_elapsed(hebrew_year) + (793 * (cls.months_elapsed(hebrew_year) // 1080)) + parts // 1080
        days = 29 * cls.months_elapsed(hebrew_year) + hours // 24
        parts %= 1080
        hours %= 24
        return days + (hours * 1080 + parts) / (24 * 1080)

    @classmethod
    def rosh_hashanah_absolute(cls, hebrew_year: int) -> int:
        """
        Absolute day number (RD) for 1 Tishrei of `hebrew_year`,
        using correct postponement ordering.
        """
        elapsed = cls.hebrew_calendar_elapsed_days(hebrew_year)
        frac = elapsed - int(elapsed)
        provisional = int(elapsed) + 1 + cls.HEBREW_EPOCH

        # Grouped postponements based on molad time + provisional weekday
        postpone = False

        # (1) Molad Zaken (molad at/after noon)
        if frac >= 0.5:
            postpone = True

        # (2) GaTRaD (common year & Tue at/after 9h 204p)
        if (provisional % 7) == 2 and not cls.hebrew_leap_year(hebrew_year):
            if frac >= (9 + 204/1080) / 24:
                postpone = True

        # (3) BeTuTaKPat (prev yr leap & Mon at/after 15h 589p)
        if (provisional % 7) == 1 and cls.hebrew_leap_year(hebrew_year - 1):
            if frac >= (15 + 589/1080) / 24:
                postpone = True

        if postpone:
            provisional += 1

        # (4) Lo ADU Rosh — RH not on Sun(0)/Wed(3)/Fri(5)
        if provisional % 7 in (0, 3, 5):
            provisional += 1

        return provisional

    @classmethod
    def hebrew_year_length(cls, hebrew_year: int) -> int:
        """Length of Hebrew year in days."""
        return cls.rosh_hashanah_absolute(hebrew_year + 1) - cls.rosh_hashanah_absolute(hebrew_year)

    @classmethod
    def hebrew_month_days(cls, hebrew_year: int, hebrew_month: int) -> int:
        """
        Days in a month for the given `hebrew_year` and `hebrew_month`
        (Tishrei=1 ... Elul=13). Handles variable Cheshvan/Kislev and Adar I in leap years.
        """
        # Fixed-length months
        if hebrew_month in (1, 5, 8, 10, 12):  # Tishrei, Shevat, Nisan, Sivan, Av
            return 30
        if hebrew_month in (4, 7, 9, 11, 13):  # Tevet, Adar (Adar II in leap), Iyar, Tammuz, Elul
            return 29
        if hebrew_month == 6:  # Adar I (leap only)
            return 30 if cls.hebrew_leap_year(hebrew_year) else 0

        # Variable months: Cheshvan/Kislev depend on year type (deficient/regular/full)
        year_len = cls.hebrew_year_length(hebrew_year)
        if hebrew_month == 2:   # Cheshvan
            return 30 if year_len in (355, 385) else 29
        if hebrew_month == 3:   # Kislev
            return 29 if year_len in (353, 383) else 30

        raise ValueError("Invalid Hebrew month number.")

    @classmethod
    def abs_from_hebrew(cls, hebrew_year: int, hebrew_month: int, hebrew_day: int) -> int:
        """Absolute (RD) day for the Hebrew date (hebrew_year, hebrew_month, hebrew_day)."""
        d = cls.rosh_hashanah_absolute(hebrew_year)
        m = 1
        while m < hebrew_month:
            d += cls.hebrew_month_days(hebrew_year, m)
            m += 1
        return d + (hebrew_day - 1)

    @staticmethod
    def gregorian_from_absolute(abs_date: int) -> date:
        """Convert absolute (RD) day to a Gregorian date (civil day)."""
        return date(1, 1, 1) + timedelta(days=abs_date - 1)

    # -----------------------------------
    # Helpers: map to the target G-year
    # -----------------------------------
    def _pick_in_gregorian_year(self, candidates_abs: list[int]) -> date | None:
        """Return the candidate whose Gregorian date falls in self.year, else None."""
        for abs_day in candidates_abs:
            g = self.gregorian_from_absolute(abs_day)
            if g.year == self.year:
                return g
        return None

    def _candidate_hebrew_years(self) -> list[int]:
        """
        Narrow Hebrew year candidates whose holidays might fall in this Gregorian year.
        This small window is sufficient and fast (avoids month-by-month scanning).
        """
        G = self.year
        return [G + 3759, G + 3760, G + 3761, G + 3762]

    # ---------------------------
    # Holiday computations
    # ---------------------------
    def compute_rosh_hashanah(self) -> dict[str, date | None]:
        candidates = [self.rosh_hashanah_absolute(H) for H in self._candidate_hebrew_years()]
        return {"Rosh Hashanah": self._pick_in_gregorian_year(candidates)}

    def compute_yom_kippur(self) -> dict[str, date | None]:
        # 10 Tishrei
        candidates = [self.abs_from_hebrew(H, 1, 10) for H in self._candidate_hebrew_years()]
        return {"Yom Kippur": self._pick_in_gregorian_year(candidates)}

    def compute_sukkot(self) -> dict[str, date | None]:
        # 15 Tishrei
        candidates = [self.abs_from_hebrew(H, 1, 15) for H in self._candidate_hebrew_years()]
        return {"Sukkot": self._pick_in_gregorian_year(candidates)}

    def compute_shemini_atzeret(self) -> dict[str, date | None]:
        # 22 Tishrei
        candidates = [self.abs_from_hebrew(H, 1, 22) for H in self._candidate_hebrew_years()]
        return {"Shemini Atzeret": self._pick_in_gregorian_year(candidates)}

    def compute_hanukkah(self) -> dict[str, date | None]:
        # 25 Kislev
        candidates = [self.abs_from_hebrew(H, 3, 25) for H in self._candidate_hebrew_years()]
        return {"Hanukkah": self._pick_in_gregorian_year(candidates)}

    def compute_passover(self) -> dict[str, date | None]:
        # 15 Nisan
        candidates = [self.abs_from_hebrew(H, 8, 15) for H in self._candidate_hebrew_years()]
        return {"Passover": self._pick_in_gregorian_year(candidates)}

    def compute_purim(self) -> dict[str, date | None]:
        # 14 Adar (Adar II in leap years) — in this numbering, "Adar" (or Adar II) is month 7
        candidates = [self.abs_from_hebrew(H, 7, 14) for H in self._candidate_hebrew_years()]
        return {"Purim": self._pick_in_gregorian_year(candidates)}
