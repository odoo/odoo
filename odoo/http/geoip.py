import functools
from typing import TYPE_CHECKING, Any, NoReturn

from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from collections.abc import Iterator

_debug = DebugLog(__name__)


class _GeoIPNull:
    __slots__ = ()

    def __getattr__(self, _name: str) -> _GeoIPNull:
        return self

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return other is self or other is None

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(None)

    def __iter__(self) -> Iterator[object]:
        return iter(())

    def __len__(self) -> int:
        return 0

    def __getitem__(self, _key: object) -> NoReturn:
        raise IndexError

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:
        return "<GeoIPNull>"


_GEOIP_NULL = _GeoIPNull()

try:
    import geoip2.database
    import geoip2.errors
    import geoip2.models
    import maxminddb

    GEOIP_EMPTY_COUNTRY = geoip2.models.Country({})
    GEOIP_EMPTY_CITY = geoip2.models.City({})
except ImportError:
    geoip2 = None
    maxminddb = None
    GEOIP_EMPTY_COUNTRY = _GEOIP_NULL
    GEOIP_EMPTY_CITY = _GEOIP_NULL


def _null_to_none(value: Any) -> Any:
    return None if value is _GEOIP_NULL else value


_GEOIP_DB_ERRORS: tuple[type[BaseException], ...] = (
    (OSError, maxminddb.InvalidDatabaseError) if maxminddb is not None else (OSError,)
)
_GEOIP_NOT_FOUND: type[BaseException] = (
    geoip2.errors.AddressNotFoundError if geoip2 is not None else LookupError
)
_GEOIP_BAD_ADDRESS: tuple[type[BaseException], ...] = (ValueError, TypeError)

_GEOIP_COUNTRY_MODEL_ATTRS = frozenset(
    {
        "continent",
        "country",
        "maxmind",
        "registered_country",
        "represented_country",
        "traits",
    }
)
_GEOIP_CITY_ONLY_MODEL_ATTRS = frozenset({"city", "location", "postal", "subdivisions"})


_GEOIP_ITEM_KEYS = frozenset(
    {
        "city",
        "country_code",
        "country_name",
        "latitude",
        "longitude",
        "region",
        "time_zone",
    }
)


class GeoIP:
    def __init__(self, ip: str | None, app: Any) -> None:
        self.app = app
        self.ip = ip

    @functools.cached_property
    def _city_record(self) -> geoip2.models.City | _GeoIPNull:
        root = self.app

        city_db = root.geoip_city_db
        if city_db is None:
            _debug.logic("http.geoip.lookup_failed", db="city", reason="no_db")
            return GEOIP_EMPTY_CITY
        try:
            record = city_db.city(self.ip)
            _debug.logic("http.geoip.resolved", db="city", found=True)
            return record
        except _GEOIP_DB_ERRORS:
            _debug.logic("http.geoip.lookup_failed", db="city", reason="db_error")
            return GEOIP_EMPTY_CITY
        except _GEOIP_NOT_FOUND:
            _debug.logic("http.geoip.lookup_failed", db="city", reason="not_found")
            return GEOIP_EMPTY_CITY
        except _GEOIP_BAD_ADDRESS:
            _debug.logic("http.geoip.lookup_failed", db="city", reason="bad_address")
            return GEOIP_EMPTY_CITY

    @functools.cached_property
    def _country_record(self) -> geoip2.models.Country | _GeoIPNull:
        root = self.app

        country_db = root.geoip_country_db
        if country_db is None:
            _debug.logic("http.geoip.lookup_failed", db="country", reason="no_db")
            return self._city_record
        try:
            record = country_db.country(self.ip)
            _debug.logic("http.geoip.resolved", db="country", found=True)
            return record
        except _GEOIP_DB_ERRORS:
            _debug.logic("http.geoip.lookup_failed", db="country", reason="db_error")
            return self._city_record
        except _GEOIP_NOT_FOUND:
            _debug.logic("http.geoip.lookup_failed", db="country", reason="not_found")
            return GEOIP_EMPTY_COUNTRY
        except _GEOIP_BAD_ADDRESS:
            _debug.logic("http.geoip.lookup_failed", db="country", reason="bad_address")
            return GEOIP_EMPTY_COUNTRY

    @property
    def country_name(self) -> str | None:
        return _null_to_none(self.country.name or self.continent.name)

    @property
    def country_code(self) -> str | None:
        return _null_to_none(self.country.iso_code or self.continent.code)

    def __getattr__(self, attr: str) -> Any:
        if geoip2 is None:
            if attr in _GEOIP_COUNTRY_MODEL_ATTRS:
                return getattr(self._country_record, attr)
            if attr in _GEOIP_CITY_ONLY_MODEL_ATTRS:
                return getattr(self._city_record, attr)
            raise AttributeError(f"{self} has no attribute {attr!r}")
        if hasattr(GEOIP_EMPTY_COUNTRY, attr):
            return getattr(self._country_record, attr)
        if hasattr(GEOIP_EMPTY_CITY, attr):
            return getattr(self._city_record, attr)
        raise AttributeError(f"{self} has no attribute {attr!r}")

    def __bool__(self) -> bool:
        return bool(self.country_name)

    def __getitem__(self, item: str) -> Any:
        match item:
            case "country_name":
                return self.country_name
            case "country_code":
                return self.country_code
            case "city":
                return _null_to_none(self.city.name)
            case "latitude":
                return _null_to_none(self.location.latitude)
            case "longitude":
                return _null_to_none(self.location.longitude)
            case "region":
                return _null_to_none(
                    self.subdivisions[0].iso_code if self.subdivisions else None
                )
            case "time_zone":
                return _null_to_none(self.location.time_zone)
            case _:
                raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        return item in _GEOIP_ITEM_KEYS

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except KeyError:
            return default

    def __iter__(self) -> Iterator[str]:
        msg = "The dictionary GeoIP API is deprecated."
        raise NotImplementedError(msg)

    def __len__(self) -> int:
        msg = "The dictionary GeoIP API is deprecated."
        raise NotImplementedError(msg)
