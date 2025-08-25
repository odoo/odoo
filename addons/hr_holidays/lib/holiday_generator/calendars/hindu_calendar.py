from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Tuple

from ..calendars.location import Location
from .utils.angles import wrap180
from .utils.phases import (
    find_phase_time_tt_near,
    lunar_phase_angle_tt_deg,
    tithi_at_local_sunrise,
    tithi_at_local_sunset,
)
from .utils.rise_set import sunrise_jd_utc, sunset_jd_utc
from .utils.side_real import find_solar_sidereal_ingress_tt_near
from .utils.time_utils import (
    from_julian_day,
    jd_tt_from_jd_ut,
    jd_ut_from_jd_tt,
    to_julian_day,
)


class HinduCalendar:
    """
    Hindu Calendar Generator (Luni-Solar, Location-Based)

    Accuracy:
        - Designed for civil and religious usage for years >= 1600 CE.
        - Implements astronomical calculations for Sun and Moon (ecliptic longitude, lunar phases, sidereal ingress).
        - Tithi determination is done via local sunrise/sunset and true lunar phase angle.
        - Major holidays (Diwali, Holi, Maha Shivaratri, Navratri, Makar Sankranti, etc.) are computed
          using astronomical rules as observed in most Indian traditions.
        - Approximations are used for some festivals where regional/panchang differences exist
          (e.g., Mahavir Jayanti, Buddha Purnima, Janmashtami).

    Algorithms Used:
        - **Tithi Calculation**: Based on angular separation between Sun and Moon (every 12° = 1 tithi).
        - **Sunrise/Sunset**: Computed from observer’s geographic location and converted to Julian Day.
        - **Lunar Phases**: Root-finding near expected phase angles (0° = Amavasya, 180° = Purnima).
        - **Sidereal Ingress**: Sun’s longitude relative to Lahiri ayanamsa (e.g., 270° = Makar Sankranti).
        - **Holiday Rules**:
            - Diwali → Amavasya (tithi 30) near Oct/Nov at local sunset.
            - Holi → Full Moon in March (Phalguna Purnima).
            - Maha Shivaratri → Krishna Chaturdashi (tithi 29) near March Amavasya.
            - Navratri → Starts day after Ashwin Amavasya (Sep/Oct new moon).
            - Dussehra → 10th day after Navratri start (Vijayadashami).
            - Janmashtami → Krishna Ashtami (tithi 23) after August/September full moon.
            - Guru Nanak Jayanti → Kartik Purnima (Nov full moon).
            - Makar Sankranti → Sidereal Sun enters Capricorn (~Jan 14).
            - Buddha Purnima → Vaishakha Purnima (May full moon).
            - Mahavir Jayanti → Chaitra Shukla Trayodashi (near April full moon).

    Limitations:
        - Regional variations (North vs. South India, Nirayana vs. Sayana systems) are not fully modeled.
        - Panchang makers may differ by a day due to sunrise/sunset thresholds and local ayanamsa values.
        - Approximations are used for leap-month handling and certain Jain/Buddhist observances.
        - This code prioritizes astronomical consistency over local almanac(the word from PvZ) differences.

    References:
        - Dershowitz, Nachum & Reingold, Edward M. *Calendrical Calculations*. Cambridge University Press.
        - Lahiri, N.C. *Indian Ephemeris and Nautical Almanac*.
        - Sewell, Robert & Dikshit, Sankara Balakrishna. *The Indian Calendar* (1896).
        - NASA JPL DE ephemerides (for solar/lunar positions).
        - B.V. Raman, *Graha and Bhava Balas* (for practical Hindu astrology/calendar rules).
        - Government of India, *National Panchang* (Rashtriya Panchang).
        - Swarajya / ISKCON publications on Janmashtami and Vaishnava calendars.
    """

    def __init__(self, location: Location):
        self.location = location
        # cache: year -> list[(kind, rounded_jd_tt)]
        self._lunations_by_year: Dict[int, List[Tuple[str, float]]] = {}

    # -------------
    # Basic utilities
    # -------------
    def tithi_at_sunrise(self, date_local: datetime) -> int:
        return tithi_at_local_sunrise(date_local, self.location)

    def tithi_at_sunset(self, date_local: datetime) -> int:
        return tithi_at_local_sunset(date_local, self.location)

    def phase_time_near(self, dt_utc: datetime, target_deg: float) -> float:
        jd_ut = to_julian_day(dt_utc)
        jd_tt = jd_tt_from_jd_ut(jd_ut)
        return find_phase_time_tt_near(jd_tt, target_deg, self.location)

    # -------------
    # Internals (year-parameterized)
    # -------------
    def _jd_ut_from_local(self, dt_local: datetime) -> float:
        """Convert a timezone-aware or naive local datetime to UT-based JD."""
        if dt_local.tzinfo is None:
            tz = timezone(timedelta(hours=self.location.tz))
            dt_local = dt_local.replace(tzinfo=tz)
        dt_utc = dt_local.astimezone(timezone.utc)
        return to_julian_day(dt_utc)

    def _tithi_at_local_clock(self, base_date: date, hour: int, minute: int) -> int:
        """Tithi number at given local clock time on base_date."""
        tz = timezone(timedelta(hours=self.location.tz))
        dt_local = datetime(base_date.year, base_date.month, base_date.day, hour, minute, 0, tzinfo=tz)
        jd_ut = self._jd_ut_from_local(dt_local)
        jd_tt = jd_tt_from_jd_ut(jd_ut)
        ang = lunar_phase_angle_tt_deg(jd_tt, False, self.location)
        return int(ang // 12.0) + 1

    def _sunrise_sunset_ut(self, base_date: date) -> Tuple[float, float]:
        """Return (sunrise_ut_jd, sunset_ut_jd) for base_date at location."""
        jd_rise = sunrise_jd_utc(datetime(base_date.year, base_date.month, base_date.day), self.location)
        jd_set = sunset_jd_utc(datetime(base_date.year, base_date.month, base_date.day), self.location)
        return jd_rise, jd_set

    def _pradosh_center_tithi(self, base_date: date) -> int:
        """Tithi at the center of Pradosh (≈72 min after sunset)."""
        _, jd_set = self._sunrise_sunset_ut(base_date)
        pradosh_center = jd_set + (72.0 / 1440.0)
        jd_tt = jd_tt_from_jd_ut(pradosh_center)
        ang = lunar_phase_angle_tt_deg(jd_tt, False, self.location)
        return int(ang // 12.0) + 1

    def _nishita_tithi(self, base_date: date) -> int:
        """Tithi at Nishita (midpoint of the night between sunset and next sunrise)."""
        _, jd_set = self._sunrise_sunset_ut(base_date)
        jd_rise_next, _ = self._sunrise_sunset_ut(base_date + timedelta(days=1))
        mid = 0.5 * (jd_set + jd_rise_next)
        jd_tt = jd_tt_from_jd_ut(mid)
        ang = lunar_phase_angle_tt_deg(jd_tt, False, self.location)
        return int(ang // 12.0) + 1

    def _aparahna_tithi(self, base_date: date) -> int:
        """Tithi at center of Aparahna (middle of last third of daytime)."""
        jd_rise, jd_set = self._sunrise_sunset_ut(base_date)
        day_len = jd_set - jd_rise
        center_last_third = jd_rise + (5.0 / 6.0) * day_len
        jd_tt = jd_tt_from_jd_ut(center_last_third)
        ang = lunar_phase_angle_tt_deg(jd_tt, False, self.location)
        return int(ang // 12.0) + 1

    # -------------
    # Lunation cache (per year)
    # -------------
    def _lunations(self, year: int) -> List[Tuple[str, float]]:
        if year not in self._lunations_by_year:
            self._lunations_by_year[year] = self._precompute_lunations(year)
        return self._lunations_by_year[year]

    def _precompute_lunations(self, year: int) -> List[Tuple[str, float]]:
        """Scan and bracket new/full moons, refine with phase root-finder.

        Returns list of (kind, rounded_jd_tt) sorted by TT.
        """
        start_utc = datetime(year, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        end_utc = datetime(year, 12, 31, tzinfo=timezone.utc) + timedelta(days=2)
        jd_tt_start = jd_tt_from_jd_ut(to_julian_day(start_utc))
        jd_tt_end = jd_tt_from_jd_ut(to_julian_day(end_utc))

        step_days = 0.04 # 30 min step for finding lunar positions
        lun_list: List[Tuple[str, float]] = []

        j = jd_tt_start
        prev_new = wrap180(lunar_phase_angle_tt_deg(j, False, self.location) - 0.0)
        prev_full = wrap180(lunar_phase_angle_tt_deg(j, False, self.location) - 180.0)

        while j < jd_tt_end:
            jn = j + step_days
            cur_new = wrap180(lunar_phase_angle_tt_deg(jn, False, self.location) - 0.0)
            cur_full = wrap180(lunar_phase_angle_tt_deg(jn, False, self.location) - 180.0)

            if prev_new == 0.0 or cur_new == 0.0 or (prev_new < 0.0 and cur_new > 0.0) or (prev_new > 0.0 and cur_new < 0.0):
                guess = 0.5 * (j + jn)
                nm_tt = find_phase_time_tt_near(guess, 0.0, self.location)
                lun_list.append(("NewMoon", nm_tt))

            if prev_full == 0.0 or cur_full == 0.0 or (prev_full < 0.0 and cur_full > 0.0) or (prev_full > 0.0 and cur_full < 0.0):
                guess = 0.5 * (j + jn)
                fm_tt = find_phase_time_tt_near(guess, 180.0, self.location)
                lun_list.append(("FullMoon", fm_tt))

            j = jn
            prev_new = cur_new
            prev_full = cur_full

        return sorted({(k, round(v, 6)) for k, v in lun_list}, key=lambda x: x[1])

    def _tt_to_local_date(self, jd_tt: float) -> Tuple[date, float]:
        """Convert TT JD to (local civil date, UT JD) at this calendar's location."""
        jd_ut = jd_ut_from_jd_tt(jd_tt)
        dt_utc = from_julian_day(jd_ut)
        return (dt_utc + timedelta(hours=self.location.tz)).date(), jd_ut

    # -------------
    # Holiday computations (ALL take year)
    # -------------
    def _compute_diwali(self, year: int) -> date:
        """
        Diwali (Kartik Amavasya), Pradosh-first rule:

        1) Pick the Oct/Nov new moon closest to Nov 1 as the seed.
        2) Prefer a date where the Pradosh-center tithi (≈72 min after sunset) is 30 (Amavasya),
        scanning a small window around the seed.
        3) If none, fall back to: sunset tithi == 30 (± up to 3 days), then sunrise tithi == 30.
        """
        # Collect Oct/Nov new moons for the given year (local date)
        diwali_candidates: List[Tuple[date, float]] = []
        for kind, jd_tt in self._lunations(year):
            if kind != "NewMoon":
                continue
            d_local, _ = self._tt_to_local_date(jd_tt)
            if d_local.year == year and d_local.month in (10, 11):
                diwali_candidates.append((d_local, jd_tt))

        # If none found (edge years), find a nearby new moon around mid-November
        if not diwali_candidates:
            from datetime import datetime, timezone
            guess_ut = to_julian_day(datetime(year, 11, 15, tzinfo=timezone.utc))
            nm_tt = find_phase_time_tt_near(jd_tt_from_jd_ut(guess_ut), 0.0, self.location)
            diwali_candidates.append((self._tt_to_local_date(nm_tt)[0], nm_tt))

        # Choose the new moon closest to Nov 1 as a seed
        from datetime import datetime, timezone, timedelta
        target_jd = to_julian_day(datetime(year, 11, 1, tzinfo=timezone.utc))
        diwali_candidates.sort(key=lambda x: abs(x[1] - target_jd))
        seed_date = diwali_candidates[0][0]

        # (1) Prefer Amavasya at Pradosh (≈72 min after sunset), scan a small window
        best = None  # tuple(score, distance, date) – score prioritizes sunset==30 as a tiebreaker
        for delta in (-2, -1, 0, 1, 2, 3):
            d = seed_date + timedelta(days=delta)
            if self._pradosh_center_tithi(d) == 30:
                score = 1 if self.tithi_at_sunset(d) == 30 else 0
                item = (score, abs(delta), d)
                best = item if best is None else min(best, item)
        if best:
            return best[2]

        # (2) Fallback: try to find sunset tithi == 30 near the seed
        chosen = seed_date
        if self.tithi_at_sunset(seed_date) != 30:
            found = None
            for delta in (1, -1, 2, -2, 3, -3):
                try_dt = seed_date + timedelta(days=delta)
                if self.tithi_at_sunset(try_dt) == 30:
                    found = try_dt
                    break
            if found is not None:
                chosen = found
            else:
                # (3) Final fallback: check sunrise tithi == 30 near the seed
                if self.tithi_at_sunrise(seed_date) == 30:
                    chosen = seed_date
                else:
                    for delta in (1, -1, 2, -2, 3, -3):
                        try_dt = seed_date + timedelta(days=delta)
                        if self.tithi_at_sunrise(try_dt) == 30:
                            chosen = try_dt
                            break

        return chosen

    def _compute_holi(self, year: int) -> date:
        """Holi (Phalguna Purnima): local date of the March full moon (simplified)."""
        holi_tt = None
        chosen_local = None
        for kind, jd_tt in self._lunations(year):
            if kind == "FullMoon":
                d_local, _ = self._tt_to_local_date(jd_tt)
                if d_local.year == year and d_local.month in (2, 3, 4):
                    if d_local.month == 3:
                        holi_tt = jd_tt
                        chosen_local = d_local
                        break
                    if holi_tt is None:
                        holi_tt = jd_tt
                        chosen_local = d_local
        if holi_tt is None:
            holi_guess_tt = jd_tt_from_jd_ut(to_julian_day(datetime(year, 3, 15, tzinfo=timezone.utc)))
            holi_tt = find_phase_time_tt_near(holi_guess_tt, 180.0, self.location)
            chosen_local = self._tt_to_local_date(holi_tt)[0]
        return chosen_local

    def _compute_maha_shivaratri(self, year: int) -> date:
        """
        Maha Shivaratri (Krishna Chaturdashi at Nishita), fixed:
        - Anchor to the new moon *nearest to March 1* (can be late Feb or early Mar).
        - Return the date whose Nishita tithi is 29 (Krishna Chaturdashi) in the 1–4 nights before that new moon.
        """
        from datetime import datetime, timezone, timedelta
        # New moon nearest to March 1 (Delhi local date may land in Feb/Mar)
        target_tt = jd_tt_from_jd_ut(to_julian_day(datetime(year, 3, 1, tzinfo=timezone.utc)))
        best = (1e9, None, None)  # (abs diff, jd_tt, local_date)

        for kind, jd_tt in self._lunations(year):
            if kind != "NewMoon":
                continue
            d_local, _ = self._tt_to_local_date(jd_tt)
            diff = abs(jd_tt - target_tt)
            if d_local.month in (2, 3) and diff < best[0]:
                best = (diff, jd_tt, d_local)

        if best[1] is None:
            # Fallback: pick absolutely nearest new moon to Mar 1
            for kind, jd_tt in self._lunations(year):
                if kind != "NewMoon":
                    continue
                d_local, _ = self._tt_to_local_date(jd_tt)
                diff = abs(jd_tt - target_tt)
                if diff < best[0]:
                    best = (diff, jd_tt, d_local)

        nm_local = best[2]

        # Look back 1–4 nights for Krishna Chaturdashi at Nishita
        for delta in (1, 2, 3, 4):
            d = nm_local - timedelta(days=delta)
            if self._nishita_tithi(d) == 29:
                return d

        # Fallback: the night before new moon
        return nm_local - timedelta(days=1)

    def _compute_navratri_start(self, year: int) -> date:
        """Navratri start: day after Ashwin Amavasya (Sep/Oct new moon)."""
        for kind, jd_tt in self._lunations(year):
            if kind == "NewMoon":
                d_local, _ = self._tt_to_local_date(jd_tt)
                if d_local.year == year and d_local.month in (9, 10):
                    return d_local + timedelta(days=1)
        nm_tt = find_phase_time_tt_near(
            jd_tt_from_jd_ut(to_julian_day(datetime(year, 9, 15, tzinfo=timezone.utc))),
            0.0,
            self.location,
        )
        return self._tt_to_local_date(nm_tt)[0] + timedelta(days=1)

    def _compute_makar_sankranti(self, year: int) -> date:
        """Makar Sankranti: sidereal Sun enters Capricorn (270° Lahiri)."""
        jan_guess_tt = jd_tt_from_jd_ut(to_julian_day(datetime(year, 1, 14, tzinfo=timezone.utc)))
        ingress_tt = find_solar_sidereal_ingress_tt_near(jan_guess_tt, 270.0)
        local_date, _ = self._tt_to_local_date(ingress_tt)
        return local_date

    def _compute_mahavir_jayanti_holiday(self, year: int) -> date:
        """Mahavir Jayanti (Chaitra Shukla Trayodashi, simplified).
        Approximation: take the April full moon (Chaitra Purnima) and search
        nearby days for sunrise tithi == 13 (Trayodashi).
        """
        # Pick April full moon or nearest to Apr 15
        fm_tt = None
        best = (1e9, None)
        target_jd = to_julian_day(datetime(year, 4, 15, tzinfo=timezone.utc))
        for kind, jd_tt in self._lunations(year):
            if kind != "FullMoon":
                continue
            d_local, _ = self._tt_to_local_date(jd_tt)
            if d_local.year == year and d_local.month == 4:
                fm_tt = jd_tt
                break
            # track nearest to Apr 15 if April not found
            diff = abs(jd_tt - target_jd)
            if diff < best[0]:
                best = (diff, jd_tt)
        if fm_tt is None:
            fm_tt = best[1]
        fm_local, _ = self._tt_to_local_date(fm_tt)
        # Search a small window around two days before full moon
        for delta in (-3, -2, -1, 0, 1):
            candidate = fm_local + timedelta(days=delta - 2)
            if self.tithi_at_sunrise(candidate) == 13:
                return candidate
        return fm_local + timedelta(days=-2)

    def _compute_buddha_purnima_holiday(self, year: int) -> date:
        """Buddha Purnima (Vaishakha Purnima, simplified): full moon in May."""
        fm_tt = None
        best = (1e9, None)
        target_jd = to_julian_day(datetime(year, 5, 15, tzinfo=timezone.utc))
        for kind, jd_tt in self._lunations(year):
            if kind != "FullMoon":
                continue
            d_local, _ = self._tt_to_local_date(jd_tt)
            if d_local.year == year and d_local.month == 5:
                fm_tt = jd_tt
                break
            diff = abs(jd_tt - target_jd)
            if diff < best[0]:
                best = (diff, jd_tt)
        if fm_tt is None:
            fm_tt = best[1]
        return self._tt_to_local_date(fm_tt)[0]

    def _compute_dussehra_holiday(self, year: int) -> date:
        """Dussehra (Vijayadashami, simplified): 10th day after Pratipada.
        Approximation: Navratri start is Shukla Pratipada, so Dussehra ≈ start + 9 days.
        """
        start = self._compute_navratri_start(year)
        return start + timedelta(days=9)

    def _compute_guru_nanak_jayanti_holiday(self, year: int) -> date:
        """Guru Nanak Jayanti (simplified): full moon in November (or nearest mid-Nov)."""
        fm_tt = None
        best = (1e9, None)
        target_jd = to_julian_day(datetime(year, 11, 15, tzinfo=timezone.utc))
        for kind, jd_tt in self._lunations(year):
            if kind != "FullMoon":
                continue
            d_local, _ = self._tt_to_local_date(jd_tt)
            if d_local.year == year and d_local.month == 11:
                fm_tt = jd_tt
                break
            diff = abs(jd_tt - target_jd)
            if diff < best[0]:
                best = (diff, jd_tt)
        if fm_tt is None:
            fm_tt = best[1]
        return self._tt_to_local_date(fm_tt)[0]

    def _compute_janmashtami_holiday(self, year: int) -> date:
        """Janmashtami (Bhadrapada Krishna Ashtami, simplified).
        Approximation: take the August full moon and search the next two weeks
        for a day where sunset tithi == 23 (Krishna Ashtami).
        """
        lun = self._lunations(year)
        fm_local = None
        # Prefer August full moon; otherwise take September
        for month_target in (8, 9):
            for kind, jd_tt in lun:
                if kind != "FullMoon":
                    continue
                d_local, _ = self._tt_to_local_date(jd_tt)
                if d_local.year == year and d_local.month == month_target:
                    fm_local = d_local
                    break
            if fm_local is not None:
                break
        if fm_local is None:
            # Fallback: nearest to Aug 15
            best = (1e9, None)
            target_jd = to_julian_day(datetime(year, 8, 15, tzinfo=timezone.utc))
            for kind, jd_tt in lun:
                if kind != "FullMoon":
                    continue
                diff = abs(jd_tt - target_jd)
                if diff < best[0]:
                    best = (diff, self._tt_to_local_date(jd_tt)[0])
            fm_local = best[1]
        # Scan next fortnight for Krishna Ashtami (tithi 23)
        for d in range(1, 15):
            day = fm_local + timedelta(days=d)
            if self.tithi_at_sunset(day) == 23:
                return day
        # Fallback approximate 8 days after full moon
        return fm_local + timedelta(days=8)
