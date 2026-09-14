import functools
import typing
import warnings
from datetime import UTC, date, datetime, time, timedelta
from typing import override

from odoo.libs.collections import FrozenOrderedSet
from odoo.libs.datetime import TIMEZONE_ALIASES, all_timezones, utc
from odoo.libs.datetime import timezone as get_timezone
from odoo.libs.debug_log import DebugLog
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.tools import SQL, OrderedSet, date_utils
from odoo.tools.date_utils import parse_date_expression, parse_iso_date

from ..constants import READ_GROUP_NUMBER_GRANULARITY
from ..domain.ast import (
    _FALSE_DOMAIN,
    Domain,
    DomainCondition,
    DomainOr,
    OptimizationLevel,
)
from ..parsing import parse_field_expr
from ..primitives import COLLECTION_TYPES
from .base import Field, _logger, _prepare_fast_get

_debug = DebugLog(__name__)


@functools.cache
def _get_all_timezones_set() -> frozenset[str]:
    return frozenset(all_timezones())


def _resolve_sql_timezone_name(env, tz_name: str) -> str | None:
    sql_names = env.backend.timezone_names(env)
    if tz_name in sql_names:
        return tz_name
    canonical = TIMEZONE_ALIASES.get(tz_name)
    if canonical is not None and canonical in sql_names:
        _debug.logic(
            "field.temporal.timezone_aliased",
            tz=tz_name,
            canonical=canonical,
        )
        return canonical
    _debug.logic("field.temporal.timezone_unknown_to_sql", tz=tz_name)
    return None


if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from odoo.tools import Query

    from .._typing import ModelLike
    from ..models import BaseModel
    from ..runtime import Environment

DATE_LENGTH = len(date.today().strftime(DATE_FORMAT))
DATETIME_LENGTH = len(datetime.now().strftime(DATETIME_FORMAT))

_TEMPORAL_COMPARISON_OPERATORS = ("in", "not in", ">", "<", "<=", ">=")


def _value_to_date(
    value: object,
    env: Environment,
    iso_only: bool = False,
) -> date | str | OrderedSet | SQL | typing.Literal[False] | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) or value is False:
        return value
    if isinstance(value, str):
        if iso_only:
            try:
                parsed: date = parse_iso_date(value)
            except ValueError:
                parse_date_expression(value, env)
                return value
        else:
            parsed = parse_date_expression(value, env)
        return _value_to_date(parsed, env)
    if isinstance(value, COLLECTION_TYPES):
        return OrderedSet(_value_to_date(v, env=env, iso_only=iso_only) for v in value)
    if isinstance(value, SQL):
        warnings.warn(
            "Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))",
            DeprecationWarning,
            stacklevel=2,
        )
        return value
    raise ValueError(f"Failed to cast {value!r} into a date")


def _value_to_datetime(
    value: object,
    env: Environment,
    iso_only: bool = False,
) -> tuple[datetime | str | OrderedSet | SQL | typing.Literal[False], bool]:
    if isinstance(value, datetime):
        if value.tzinfo:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return value, False
    if value is False:
        return False, True
    if isinstance(value, str):
        if iso_only:
            try:
                parsed: date = parse_iso_date(value)
            except ValueError:
                _dt, is_date = _value_to_datetime(
                    parse_date_expression(value, env), env
                )
                return value, is_date
        else:
            parsed = parse_date_expression(value, env)
        return _value_to_datetime(parsed, env)
    if isinstance(value, date):
        tz = None if value.year in (1, 9999) else env.tz
        if tz == utc:
            tz = None
        value = datetime.combine(value, time.min, tz)
        if tz is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return value, True
    if isinstance(value, COLLECTION_TYPES):
        if not value:
            return OrderedSet(), True
        converted, is_date = zip(
            *(_value_to_datetime(v, env=env, iso_only=iso_only) for v in value),
            strict=False,
        )
        return OrderedSet(converted), all(is_date)
    if isinstance(value, SQL):
        warnings.warn(
            "Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))",
            DeprecationWarning,
            stacklevel=2,
        )
        return value, False
    raise ValueError(f"Failed to cast {value!r} into a datetime")


def _end_of_local_day(start: datetime, env: Environment) -> datetime:
    tz = env.tz
    if tz is None or tz == utc:
        return start + timedelta(days=1)
    local_date = start.replace(tzinfo=UTC).astimezone(tz).date()
    end, _is_date = _value_to_datetime(local_date + timedelta(days=1), env)
    if not isinstance(end, datetime):
        raise TypeError(f"a date did not convert to a datetime: {end!r}")
    return end


def _is_relative_temporal_value(condition: DomainCondition) -> bool:
    value = condition.value
    return (
        condition.operator in _TEMPORAL_COMPARISON_OPERATORS
        and "." not in condition.field_expr
        and isinstance(value, (str, FrozenOrderedSet))
        and (
            not isinstance(value, FrozenOrderedSet)
            or any(isinstance(v, str) for v in value)
        )
    )


class BaseDate[T: date](Field[T | typing.Literal[False]]):
    is_temporal = True

    start_of = staticmethod(date_utils.start_of)
    end_of = staticmethod(date_utils.end_of)
    add = staticmethod(date_utils.add)
    subtract = staticmethod(date_utils.subtract)

    def get_expression_getter(
        self, field_expr: str
    ) -> Callable[[BaseModel], typing.Any]:
        _fname, property_name = parse_field_expr(field_expr)
        if not property_name:
            return super().get_expression_getter(field_expr)

        get_value = self.__get__
        get_property = self._get_expression_property_getter(property_name)
        return lambda record: (value := get_value(record)) and get_property(value)

    def _get_expression_property_getter(
        self, property_name: str
    ) -> Callable[[T], typing.Any]:
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
                return lambda value: value.isoweekday() % 7
            case "hour_number" if self.is_datetime:
                return lambda value: typing.cast("datetime", value).hour
            case "minute_number" if self.is_datetime:
                return lambda value: typing.cast("datetime", value).minute
            case "second_number" if self.is_datetime:
                return lambda value: typing.cast("datetime", value).second
            case "hour_number" | "minute_number" | "second_number":
                return lambda value: 0
        assert property_name not in READ_GROUP_NUMBER_GRANULARITY, (
            f"Property not implemented {property_name}"
        )
        raise ValueError(
            f"Error when processing the granularity {property_name} is not supported. "
            f"Only {', '.join(READ_GROUP_NUMBER_GRANULARITY.keys())} are supported"
        )

    def property_to_sql(
        self,
        field_sql: SQL,
        property_name: str,
        model: ModelLike,
        alias: str,
        query: Query,
    ) -> SQL:
        sql_expr = field_sql
        if self.is_datetime and (tz_name := model.env.context.get("tz")):
            if sql_tz := _resolve_sql_timezone_name(model.env, tz_name):
                sql_expr = SQL(
                    "timezone(%s, timezone('UTC', %s))",
                    SQL.literal(sql_tz),
                    sql_expr,
                )
            else:
                _logger.warning(
                    "Grouping in UTC: the database does not know timezone %r", tz_name
                )
        _debug.logic(
            "field.temporal.property_to_sql",
            model=model._name,
            field=self.name,
            property=property_name,
            tz=model.env.context.get("tz") if self.is_datetime else None,
            tz_applied=sql_expr is not field_sql,
        )
        if property_name == "tz":
            return sql_expr
        if property_name not in READ_GROUP_NUMBER_GRANULARITY:
            raise ValueError(
                f"Error when processing the granularity {property_name} is not supported. Only {', '.join(READ_GROUP_NUMBER_GRANULARITY.keys())} are supported"
            )
        granularity = READ_GROUP_NUMBER_GRANULARITY[property_name]
        return SQL(  # noqa: E8501  granularity is a value of a module constant
            "date_part('%s', %%s)" % granularity, sql_expr
        )

    @override
    def convert_to_column(
        self,
        value,
        record: ModelLike,
        values: dict | None = None,
        validate: bool = True,
    ) -> typing.Any:
        return self.convert_to_cache(value, record, validate=validate)


class Date(BaseDate[date]):
    type = "date"
    is_date = True
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_orderable = True
    cache_is_read_value = True
    _column_type = ("date", "date")

    if not typing.TYPE_CHECKING:
        __get__ = _prepare_fast_get(
            lambda field, value, record: False if value is None else value
        )

    @override
    def _optimize_condition(
        self, condition: DomainCondition, model: BaseModel, level: OptimizationLevel
    ) -> Domain:
        operator = condition.operator
        if level == OptimizationLevel.BASIC:
            if (
                operator not in _TEMPORAL_COMPARISON_OPERATORS
                or "." in condition.field_expr
            ):
                return condition
            value = _value_to_date(condition.value, model.env, iso_only=True)
            if value is False and operator[0] in ("<", ">"):
                _debug.logic(
                    "field.date.false_comparison_collapsed",
                    model=model._name,
                    field=condition.field_expr,
                    operator=operator,
                )
                return _FALSE_DOMAIN
            return DomainCondition(condition.field_expr, operator, value)
        if level == OptimizationLevel.DYNAMIC_VALUES and _is_relative_temporal_value(
            condition
        ):
            value = _value_to_date(condition.value, model.env)
            _debug.logic(
                "field.date.relative_resolved",
                model=model._name,
                field=condition.field_expr,
                operator=operator,
                value=value,
            )
            return DomainCondition(condition.field_expr, operator, value)
        return condition

    @staticmethod
    def today(*args) -> date:
        return date.today()

    @staticmethod
    def context_today(record: BaseModel, timestamp: datetime | None = None) -> date:
        today = timestamp or datetime.now()
        tz = record.env.tz
        today_utc = today.replace(tzinfo=utc)
        today = today_utc.astimezone(tz)
        return today.date()

    @staticmethod
    def to_date(
        value: str | date | datetime | typing.Literal[False] | None,
    ) -> date | None:
        if not value:
            return None
        if isinstance(value, date):
            if isinstance(value, datetime):
                return value.date()
            return value
        if not isinstance(value, str):
            raise TypeError(f"expected str or date, got {value!r}")
        value = value[:DATE_LENGTH]
        try:
            return date.fromisoformat(value)
        except ValueError:
            return datetime.strptime(value, DATE_FORMAT).date()

    from_string = to_date

    @staticmethod
    def to_string(
        value: date | typing.Literal[False],
    ) -> str | typing.Literal[False]:
        return value.strftime(DATE_FORMAT) if value else False

    @override
    def convert_to_cache(
        self, value, record: ModelLike, validate: bool = True
    ) -> typing.Any:
        if not value:
            return None
        return self.to_date(value)

    @override
    def convert_to_export(self, value: typing.Any, record: ModelLike) -> typing.Any:
        return self.to_date(value) or ""

    @override
    def convert_to_display_name(
        self, value: typing.Any, record: ModelLike
    ) -> str | typing.Literal[False]:
        return Date.to_string(value)


class Datetime(BaseDate[datetime]):
    type = "datetime"
    is_datetime = True
    cache_is_record_value = True
    cache_truthiness_matches = True
    cache_is_orderable = True
    cache_is_read_value = True
    _column_type = ("timestamp", "timestamp")

    if not typing.TYPE_CHECKING:
        __get__ = _prepare_fast_get(
            lambda field, value, record: False if value is None else value
        )

    @override
    def _optimize_condition(
        self, condition: DomainCondition, model: BaseModel, level: OptimizationLevel
    ) -> Domain:
        if level == OptimizationLevel.BASIC:
            return self._optimize_datetime_comparand(condition, model)
        if level == OptimizationLevel.DYNAMIC_VALUES and _is_relative_temporal_value(
            condition
        ):
            env = model.env

            def parse(v):
                return parse_date_expression(v, env) if isinstance(v, str) else v

            value = condition.value
            resolved = (
                OrderedSet(parse(v) for v in value)
                if isinstance(value, FrozenOrderedSet)
                else parse(value)
            )
            _debug.logic(
                "field.datetime.relative_resolved",
                model=model._name,
                field=condition.field_expr,
                operator=condition.operator,
            )
            return DomainCondition(condition.field_expr, condition.operator, resolved)
        return condition

    @staticmethod
    def _optimize_datetime_comparand(
        condition: DomainCondition, model: BaseModel
    ) -> Domain:
        field_expr = condition.field_expr
        operator = condition.operator
        if operator not in _TEMPORAL_COMPARISON_OPERATORS or "." in field_expr:
            return condition
        value = condition.value
        dates: set = set()
        if isinstance(value, COLLECTION_TYPES):
            pairs = [_value_to_datetime(v, model.env, iso_only=True) for v in value]
            value = FrozenOrderedSet(v for v, _is_date in pairs)
            dates = {v for v, is_date in pairs if is_date and isinstance(v, datetime)}
            is_date = False
        else:
            value, is_date = _value_to_datetime(value, model.env, iso_only=True)

        if operator[0] in ("<", ">"):
            if value is False:
                return _FALSE_DOMAIN
            if not isinstance(value, datetime):
                return condition
            if is_date:
                if operator == ">":
                    try:
                        value = _end_of_local_day(value, model.env)
                    except OverflowError:
                        return _FALSE_DOMAIN
                    operator = ">="
                elif operator == "<=":
                    try:
                        value = _end_of_local_day(value, model.env)
                    except OverflowError:
                        return DomainCondition(field_expr, "!=", False)
                    operator = "<"

        if operator in ("in", "not in") and isinstance(value, COLLECTION_TYPES):
            day_values = OrderedSet(v for v in value if v in dates)
            if day_values:

                def whole_day(v: datetime) -> Domain:
                    try:
                        end = _end_of_local_day(v, model.env)
                    except OverflowError:
                        return DomainCondition(field_expr, ">=", v)
                    return DomainCondition(field_expr, ">=", v) & DomainCondition(
                        field_expr, "<", end
                    )

                domain = DomainOr.apply(whole_day(v) for v in day_values)
                if exact := OrderedSet(v for v in value if v not in day_values):
                    domain |= DomainCondition(field_expr, "in", exact)
                if operator == "not in":
                    domain = ~domain
                _debug.logic(
                    "field.datetime.whole_day_expanded",
                    model=model._name,
                    field=field_expr,
                    operator=operator,
                    days=len(day_values),
                    exact=len(value) - len(day_values),
                )
                return domain

        if operator == condition.operator and (
            value is condition.value
            or (
                value.__class__ is condition.value.__class__
                and value == condition.value
            )
        ):
            return condition
        return DomainCondition(field_expr, operator, value)

    @staticmethod
    def now(*args) -> datetime:
        return datetime.now().replace(microsecond=0)

    @staticmethod
    def today(*args) -> datetime:
        return Datetime.now().replace(hour=0, minute=0, second=0)

    @staticmethod
    def context_timestamp(record: ModelLike, timestamp: datetime) -> datetime:
        assert isinstance(timestamp, datetime), "Datetime instance expected"
        tz = record.env.tz
        utc_timestamp = timestamp.replace(tzinfo=utc)
        return utc_timestamp.astimezone(tz)

    @staticmethod
    def to_datetime(
        value: str | date | datetime | typing.Literal[False] | None,
    ) -> datetime | None:
        if not value:
            return None
        if isinstance(value, date):
            if isinstance(value, datetime):
                if value.tzinfo:
                    if value.tzinfo is UTC or value.tzinfo == UTC:
                        return value.replace(tzinfo=None)
                    return value.astimezone(UTC).replace(tzinfo=None)
                return value
            return datetime.combine(value, time.min)

        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            value = value[:DATETIME_LENGTH]
            parsed = datetime.strptime(value, DATETIME_FORMAT[: len(value) - 2])
        if parsed.tzinfo:
            return parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed

    from_string = to_datetime

    @staticmethod
    def to_string(
        value: datetime | typing.Literal[False],
    ) -> str | typing.Literal[False]:
        return value.strftime(DATETIME_FORMAT) if value else False

    def get_expression_getter(
        self, field_expr: str
    ) -> Callable[[BaseModel], typing.Any]:
        if field_expr == self.name:
            return self.__get__
        _fname, property_name = parse_field_expr(field_expr)
        if property_name is None:
            return super().get_expression_getter(field_expr)
        get_property = self._get_expression_property_getter(property_name)

        def getter(record):
            dt = self.__get__(record)
            if not dt:
                return False
            if (
                tz_name := record.env.context.get("tz")
            ) and tz_name in _get_all_timezones_set():
                dt = dt.replace(tzinfo=utc).astimezone(get_timezone(tz_name))
            return get_property(dt)

        return getter

    @override
    def convert_to_cache(
        self, value, record: ModelLike, validate: bool = True
    ) -> typing.Any:
        return self.to_datetime(value)

    @override
    def convert_to_export(self, value: typing.Any, record: ModelLike) -> typing.Any:
        value = self.convert_to_display_name(value, record)
        return self.to_datetime(value) or ""

    @override
    def convert_to_display_name(
        self, value: typing.Any, record: ModelLike
    ) -> str | typing.Literal[False]:
        if not value:
            return False
        return Datetime.to_string(Datetime.context_timestamp(record, value))
