import functools
import typing
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timezone
from typing import override

from odoo.libs.datetime import utc
from odoo.libs.datetime.tz import all_timezones
from odoo.libs.datetime.tz import timezone as get_timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.tools import SQL, date_utils

from ..constants import READ_GROUP_NUMBER_GRANULARITY
from ..parsing import parse_field_expr
from .base import Field, _logger, _make_scalar_get


@functools.cache
def _get_all_timezones_set() -> frozenset[str]:
    """Cached set of all available timezones for fast lookup."""
    return frozenset(all_timezones())

if typing.TYPE_CHECKING:
    from odoo.tools import Query

    from ..models import BaseModel

T = typing.TypeVar("T")

DATE_LENGTH = len(date.today().strftime(DATE_FORMAT))
DATETIME_LENGTH = len(datetime.now().strftime(DATETIME_FORMAT))


class BaseDate[T](Field[T | typing.Literal[False]]):
    """Common field properties for Date and Datetime."""

    start_of = staticmethod(date_utils.start_of)
    end_of = staticmethod(date_utils.end_of)
    add = staticmethod(date_utils.add)
    subtract = staticmethod(date_utils.subtract)

    def expression_getter(self, field_expr: str) -> Callable[[BaseModel], typing.Any]:
        _fname, property_name = parse_field_expr(field_expr)
        if not property_name:
            return super().expression_getter(field_expr)

        get_value = self.__get__
        get_property = self._expression_property_getter(property_name)
        return lambda record: (value := get_value(record)) and get_property(value)

    def _expression_property_getter(
        self, property_name: str
    ) -> Callable[[T], typing.Any]:
        """Return a function that maps a field value (date or datetime) to the
        given ``property_name``.
        """
        match property_name:
            case "tz":
                return lambda value: value
            case "year_number":
                return lambda value: value.year
            case "quarter_number":
                return lambda value: (value.month - 1) // 3 + 1
            case "month_number":
                return lambda value: value.month
            case "iso_week_number":
                return lambda value: value.isocalendar().week
            case "day_of_year":
                return lambda value: value.timetuple().tm_yday
            case "day_of_month":
                return lambda value: value.day
            case "day_of_week":
                return lambda value: value.timetuple().tm_wday
            case "hour_number" if self.type == "datetime":
                return lambda value: value.hour
            case "minute_number" if self.type == "datetime":
                return lambda value: value.minute
            case "second_number" if self.type == "datetime":
                return lambda value: value.second
            case "hour_number" | "minute_number" | "second_number":
                # for dates, it is always 0
                return lambda value: 0
        assert (
            property_name not in READ_GROUP_NUMBER_GRANULARITY
        ), f"Property not implemented {property_name}"
        raise ValueError(
            f"Error when processing the granularity {property_name} is not supported. "
            f"Only {', '.join(READ_GROUP_NUMBER_GRANULARITY.keys())} are supported"
        )

    def property_to_sql(
        self,
        field_sql: SQL,
        property_name: str,
        model: BaseModel,
        alias: str,
        query: Query,
    ) -> SQL:
        sql_expr = field_sql
        if self.type == "datetime" and (tz_name := model.env.context.get("tz")):
            # only use the timezone from the context
            if tz_name in _get_all_timezones_set():
                # Embed timezone as SQL literal (not parameter) so that the
                # expression is identical in SELECT and GROUP BY.  With
                # server-side binding, each %s gets a unique $N, making
                # PostgreSQL see SELECT and GROUP BY as different expressions.
                sql_expr = SQL(
                    "timezone('%s', timezone('UTC', %%s))" % tz_name, sql_expr
                )
            else:
                _logger.warning("Grouping in unknown / legacy timezone %r", tz_name)
        if property_name == "tz":
            # set only the timezone
            return sql_expr
        if property_name not in READ_GROUP_NUMBER_GRANULARITY:
            raise ValueError(
                f'Error when processing the granularity {property_name} is not supported. Only {", ".join(READ_GROUP_NUMBER_GRANULARITY.keys())} are supported'
            )
        granularity = READ_GROUP_NUMBER_GRANULARITY[property_name]
        # Embed granularity as SQL literal for GROUP BY consistency (see above).
        return SQL("date_part('%s', %%s)" % granularity, sql_expr)

    @override
    def convert_to_column(
        self,
        value,
        record: BaseModel,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        return self.convert_to_cache(value, record, validate=validate)


class Date(BaseDate[date]):
    """Encapsulates a python :class:`date <datetime.date>` object."""

    type = "date"
    _column_type = ("date", "date")

    __get__ = _make_scalar_get(lambda v: False if v is None else v)

    @staticmethod
    def today(*args) -> date:
        """Return the current day in the format expected by the ORM.

        .. note:: This function may be used to compute default values.
        """
        return date.today()

    @staticmethod
    def context_today(
        record: BaseModel, timestamp: date | datetime | None = None
    ) -> date:
        """Return the current date as seen in the client's timezone in a format
        fit for date fields.

        .. note:: This method may be used to compute default values.

        :param record: recordset from which the timezone will be obtained.
        :param timestamp: optional datetime value to use instead of
            the current date and time (must be a datetime, regular dates
            can't be converted between timezones).
        """
        today = timestamp or datetime.now()
        tz = record.env.tz
        today_utc = today.replace(tzinfo=utc)  # UTC = no DST
        today = today_utc.astimezone(tz)
        return today.date()

    @staticmethod
    def to_date(
        value: str | date | datetime | typing.Literal[False] | None,
    ) -> date | None:
        """Attempt to convert ``value`` to a :class:`date` object.

        .. warning::

            If a datetime object is given as value,
            it will be converted to a date object and all
            datetime-specific information will be lost (HMS, TZ, ...).

        :param value: value to convert.
        :type value: str or date or datetime
        :return: an object representing ``value``.
        """
        if not value:
            return None
        if isinstance(value, date):
            if isinstance(value, datetime):
                return value.date()
            return value
        # fromisoformat (C-level) is ~44x faster than strptime for ISO dates
        return date.fromisoformat(value[:DATE_LENGTH])

    # kept for backwards compatibility, but consider `from_string` as deprecated, will probably
    # be removed after V12
    from_string = to_date

    @staticmethod
    def to_string(
        value: date | typing.Literal[False],
    ) -> str | typing.Literal[False]:
        """
        Convert a :class:`date` or :class:`datetime` object to a string.

        :param value: value to convert.
        :return: a string representing ``value`` in the server's date format, if ``value`` is of
            type :class:`datetime`, the hours, minute, seconds, tzinfo will be truncated.
        """
        return value.strftime(DATE_FORMAT) if value else False

    @override
    def convert_to_cache(
        self, value, record: BaseModel, validate: bool = True
    ) -> typing.Any:
        if not value:
            return None
        if isinstance(value, datetime):
            # Defensive: some data files (e.g., CRM demo data) pass datetime
            # objects to Date fields.  Silently truncate to date rather than
            # raising, since the time component carries no meaning here.
            value = value.date()
        return self.to_date(value)

    @override
    def convert_to_export(self, value, record: BaseModel) -> typing.Any:
        return self.to_date(value) or ""

    @override
    def convert_to_display_name(
        self, value, record: BaseModel
    ) -> str | typing.Literal[False]:
        return Date.to_string(value)


class Datetime(BaseDate[datetime]):
    """Encapsulates a python :class:`datetime <datetime.datetime>` object."""

    type = "datetime"
    _column_type = ("timestamp", "timestamp")

    __get__ = _make_scalar_get(lambda v: False if v is None else v)

    @staticmethod
    def now(*args) -> datetime:
        """Return the current day and time in the format expected by the ORM.

        .. note:: This function may be used to compute default values.
        """
        # microseconds must be annihilated as they don't comply with the server datetime format
        return datetime.now().replace(microsecond=0)

    @staticmethod
    def today(*args) -> datetime:
        """Return the current day, at midnight (00:00:00)."""
        return Datetime.now().replace(hour=0, minute=0, second=0)

    @staticmethod
    def context_timestamp(record: BaseModel, timestamp: datetime) -> datetime:
        """Return the given timestamp converted to the client's timezone.

        .. note:: This method is *not* meant for use as a default initializer,
            because datetime fields are automatically converted upon
            display on client side. For default values, :meth:`now`
            should be used instead.

        :param record: recordset from which the timezone will be obtained.
        :param datetime timestamp: naive datetime value (expressed in UTC)
            to be converted to the client timezone.
        :return: timestamp converted to timezone-aware datetime in context timezone.
        :rtype: datetime
        """
        assert isinstance(timestamp, datetime), "Datetime instance expected"
        tz = record.env.tz
        utc_timestamp = timestamp.replace(tzinfo=utc)  # UTC = no DST
        return utc_timestamp.astimezone(tz)

    @staticmethod
    def to_datetime(
        value: str | date | datetime | typing.Literal[False] | None,
    ) -> datetime | None:
        """Convert an ORM ``value`` into a :class:`datetime` value.

        Accepts timezone-aware UTC datetimes and converts them to naive UTC.

        :param value: value to convert.
        :type value: str or date or datetime
        :return: an object representing ``value`` as a naive UTC datetime.
        """
        if not value:
            return None
        if isinstance(value, date):
            if isinstance(value, datetime):
                if value.tzinfo:
                    # Accept UTC-aware datetimes, convert to naive UTC
                    if value.tzinfo is UTC or value.tzinfo == UTC:
                        return value.replace(tzinfo=None)
                    # Non-UTC aware datetimes: convert to UTC then strip
                    return value.astimezone(UTC).replace(tzinfo=None)
                return value
            return datetime.combine(value, time.min)

        # fromisoformat (C-level) is ~61x faster than strptime for ISO datetimes
        return datetime.fromisoformat(value)

    # kept for backwards compatibility, but consider `from_string` as deprecated, will probably
    # be removed after V12
    from_string = to_datetime

    @staticmethod
    def to_string(
        value: datetime | typing.Literal[False],
    ) -> str | typing.Literal[False]:
        """Convert a :class:`datetime` or :class:`date` object to a string.

        :param value: value to convert.
        :type value: datetime or date
        :return: a string representing ``value`` in the server's datetime format,
            if ``value`` is of type :class:`date`,
            the time portion will be midnight (00:00:00).
        """
        return value.strftime(DATETIME_FORMAT) if value else False

    def expression_getter(self, field_expr: str) -> Callable[[BaseModel], typing.Any]:
        if field_expr == self.name:
            return self.__get__
        _fname, property_name = parse_field_expr(field_expr)
        get_property = self._expression_property_getter(property_name)

        def getter(record):
            dt = self.__get__(record)
            if not dt:
                return False
            if (
                tz_name := record.env.context.get("tz")
            ) and tz_name in _get_all_timezones_set():
                # only use the timezone from the context
                dt = dt.astimezone(get_timezone(tz_name))
            return get_property(dt)

        return getter

    @override
    def convert_to_cache(
        self, value, record: BaseModel, validate: bool = True
    ) -> typing.Any:
        return self.to_datetime(value)

    @override
    def convert_to_export(self, value, record: BaseModel) -> typing.Any:
        value = self.convert_to_display_name(value, record)
        return self.to_datetime(value) or ""

    @override
    def convert_to_display_name(
        self, value, record: BaseModel
    ) -> str | typing.Literal[False]:
        if not value:
            return False
        return Datetime.to_string(Datetime.context_timestamp(record, value))
