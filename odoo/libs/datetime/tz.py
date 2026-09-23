__all__ = [
    "TIMEZONE_ALIASES",
    "all_timezones",
    "country_timezones",
    "localize_standard",
    "timezone",
    "utc",
]

from collections.abc import Mapping
from datetime import UTC, datetime
from datetime import timezone as dt_timezone
from types import MappingProxyType
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from babel.core import get_global

utc = UTC

TIMEZONE_ALIASES: dict[str, str] = {
    "Africa/Asmera": "Africa/Nairobi",
    "America/Argentina/ComodRivadavia": "America/Argentina/Catamarca",
    "America/Buenos_Aires": "America/Argentina/Buenos_Aires",
    "America/Cordoba": "America/Argentina/Cordoba",
    "America/Fort_Wayne": "America/Indiana/Indianapolis",
    "America/Indianapolis": "America/Indiana/Indianapolis",
    "America/Jujuy": "America/Argentina/Jujuy",
    "America/Knox_IN": "America/Indiana/Knox",
    "America/Louisville": "America/Kentucky/Louisville",
    "America/Mendoza": "America/Argentina/Mendoza",
    "America/Rosario": "America/Argentina/Cordoba",
    "Antarctica/South_Pole": "Pacific/Auckland",
    "Asia/Ashkhabad": "Asia/Ashgabat",
    "Asia/Calcutta": "Asia/Kolkata",
    "Asia/Choibalsan": "Asia/Ulaanbaatar",
    "Asia/Chungking": "Asia/Shanghai",
    "Asia/Dacca": "Asia/Dhaka",
    "Asia/Katmandu": "Asia/Kathmandu",
    "Asia/Macao": "Asia/Macau",
    "Asia/Rangoon": "Asia/Yangon",
    "Asia/Saigon": "Asia/Ho_Chi_Minh",
    "Asia/Thimbu": "Asia/Thimphu",
    "Asia/Ujung_Pandang": "Asia/Makassar",
    "Asia/Ulan_Bator": "Asia/Ulaanbaatar",
    "Atlantic/Faeroe": "Atlantic/Faroe",
    "Australia/ACT": "Australia/Sydney",
    "Australia/LHI": "Australia/Lord_Howe",
    "Australia/North": "Australia/Darwin",
    "Australia/NSW": "Australia/Sydney",
    "Australia/Queensland": "Australia/Brisbane",
    "Australia/South": "Australia/Adelaide",
    "Australia/Tasmania": "Australia/Hobart",
    "Australia/Victoria": "Australia/Melbourne",
    "Australia/West": "Australia/Perth",
    "Brazil/Acre": "America/Rio_Branco",
    "Brazil/DeNoronha": "America/Noronha",
    "Brazil/East": "America/Sao_Paulo",
    "Brazil/West": "America/Manaus",
    "CET": "Europe/Brussels",
    "CST6CDT": "America/Chicago",
    "Canada/Atlantic": "America/Halifax",
    "Canada/Central": "America/Winnipeg",
    "Canada/Eastern": "America/Toronto",
    "Canada/Mountain": "America/Edmonton",
    "Canada/Newfoundland": "America/St_Johns",
    "Canada/Pacific": "America/Vancouver",
    "Canada/Saskatchewan": "America/Regina",
    "Canada/Yukon": "America/Whitehorse",
    "Chile/Continental": "America/Santiago",
    "Chile/EasterIsland": "Pacific/Easter",
    "Cuba": "America/Havana",
    "EET": "Europe/Athens",
    "EST": "America/Panama",
    "EST5EDT": "America/New_York",
    "Egypt": "Africa/Cairo",
    "Eire": "Europe/Dublin",
    "Europe/Kiev": "Europe/Kyiv",
    "Europe/Uzhgorod": "Europe/Kyiv",
    "Europe/Zaporozhye": "Europe/Kyiv",
    "GB": "Europe/London",
    "GB-Eire": "Europe/London",
    "GMT+0": "Etc/GMT",
    "GMT-0": "Etc/GMT",
    "GMT0": "Etc/GMT",
    "Greenwich": "Etc/GMT",
    "HST": "Pacific/Honolulu",
    "Hongkong": "Asia/Hong_Kong",
    "Iceland": "Africa/Abidjan",
    "Iran": "Asia/Tehran",
    "Israel": "Asia/Jerusalem",
    "Jamaica": "America/Jamaica",
    "Japan": "Asia/Tokyo",
    "Kwajalein": "Pacific/Kwajalein",
    "Libya": "Africa/Tripoli",
    "MET": "Europe/Brussels",
    "MST": "America/Phoenix",
    "MST7MDT": "America/Denver",
    "Mexico/BajaNorte": "America/Tijuana",
    "Mexico/BajaSur": "America/Mazatlan",
    "Mexico/General": "America/Mexico_City",
    "Navajo": "America/Denver",
    "NZ": "Pacific/Auckland",
    "NZ-CHAT": "Pacific/Chatham",
    "PST8PDT": "America/Los_Angeles",
    "Pacific/Enderbury": "Pacific/Kanton",
    "Pacific/Ponape": "Pacific/Guadalcanal",
    "Pacific/Truk": "Pacific/Port_Moresby",
    "Poland": "Europe/Warsaw",
    "Portugal": "Europe/Lisbon",
    "PRC": "Asia/Shanghai",
    "ROC": "Asia/Taipei",
    "ROK": "Asia/Seoul",
    "Singapore": "Asia/Singapore",
    "Turkey": "Europe/Istanbul",
    "UCT": "Etc/UTC",
    "Universal": "Etc/UTC",
    "US/Alaska": "America/Anchorage",
    "US/Aleutian": "America/Adak",
    "US/Arizona": "America/Phoenix",
    "US/Central": "America/Chicago",
    "US/Eastern": "America/New_York",
    "US/East-Indiana": "America/Indiana/Indianapolis",
    "US/Hawaii": "Pacific/Honolulu",
    "US/Indiana-Starke": "America/Indiana/Knox",
    "US/Michigan": "America/Detroit",
    "US/Mountain": "America/Denver",
    "US/Pacific": "America/Los_Angeles",
    "US/Samoa": "Pacific/Pago_Pago",
    "W-SU": "Europe/Moscow",
    "WET": "Europe/Lisbon",
    "Zulu": "Etc/UTC",
}

_timezone_cache: dict[str, ZoneInfo] = {}
_available_timezones: frozenset[str] = frozenset(available_timezones())


def timezone(name: str) -> ZoneInfo:
    if name in _timezone_cache:
        return _timezone_cache[name]

    if name.upper() == "UTC":
        tz = ZoneInfo("UTC")
        _timezone_cache[name] = tz
        return tz

    if name in _available_timezones:
        tz = ZoneInfo(name)
        _timezone_cache[name] = tz
        return tz

    canonical_name = TIMEZONE_ALIASES.get(name)
    if canonical_name is not None:
        try:
            tz = ZoneInfo(canonical_name)
            _timezone_cache[name] = tz
            return tz
        except KeyError:
            pass

    try:
        tz = ZoneInfo(name)
    except KeyError, ValueError:
        raise ZoneInfoNotFoundError(f"Unknown timezone: {name!r}") from None

    _timezone_cache[name] = tz
    return tz


def localize_standard(dt: datetime, tz: ZoneInfo | dt_timezone) -> datetime:
    if dt.tzinfo is not None:
        raise ValueError(f"Cannot localize a datetime that already has tzinfo: {dt}")
    first = dt.replace(tzinfo=tz)
    second = dt.replace(tzinfo=tz, fold=1)
    if first.utcoffset() == second.utcoffset():
        return first
    if first.astimezone(UTC).astimezone(tz).replace(tzinfo=None) == dt:
        return second
    return first


def all_timezones() -> frozenset[str]:
    return _available_timezones


_country_timezones: Mapping[str, tuple[str, ...]] | None = None


def country_timezones() -> Mapping[str, tuple[str, ...]]:
    global _country_timezones  # noqa: PLW0603  one-shot lazy build of the country->tz map
    if _country_timezones is None:
        zone_territories = get_global("zone_territories")
        grouped: dict[str, list[str]] = {}
        for tz_name, country_code in zone_territories.items():
            grouped.setdefault(country_code, []).append(tz_name)
        _country_timezones = MappingProxyType(
            {code: tuple(zones) for code, zones in grouped.items()}
        )
    return _country_timezones
