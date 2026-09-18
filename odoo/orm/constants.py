from typing import TYPE_CHECKING, Final

import dateutil.relativedelta

from odoo.libs.sql import SQL

if TYPE_CHECKING:
    from collections.abc import Callable

READ_GROUP_TIME_GRANULARITY: Final[dict[str, dateutil.relativedelta.relativedelta]] = {
    "hour": dateutil.relativedelta.relativedelta(hours=1),
    "day": dateutil.relativedelta.relativedelta(days=1),
    "week": dateutil.relativedelta.relativedelta(days=7),
    "month": dateutil.relativedelta.relativedelta(months=1),
    "quarter": dateutil.relativedelta.relativedelta(months=3),
    "year": dateutil.relativedelta.relativedelta(years=1),
}

READ_GROUP_NUMBER_GRANULARITY: Final[dict[str, str]] = {
    "year_number": "year",
    "quarter_number": "quarter",
    "month_number": "month",
    "iso_week_number": "week",
    "day_of_year": "doy",
    "day_of_month": "day",
    "day_of_week": "dow",
    "hour_number": "hour",
    "minute_number": "minute",
    "second_number": "second",
}

READ_GROUP_ALL_TIME_GRANULARITY: Final[
    dict[str, dateutil.relativedelta.relativedelta | str]
] = READ_GROUP_TIME_GRANULARITY | READ_GROUP_NUMBER_GRANULARITY

SQL_ORDER_DIR: Final[dict[str, SQL]] = {"ASC": SQL("ASC"), "DESC": SQL("DESC")}
SQL_ORDER_NULLS: Final[dict[str, SQL]] = {
    "NULLS FIRST": SQL("NULLS FIRST"),
    "NULLS LAST": SQL("NULLS LAST"),
}


def _array_agg(table: str, expr: SQL) -> SQL:
    return SQL("ARRAY_AGG(%s ORDER BY %s)", expr, SQL.identifier(table, "id"))


READ_GROUP_AGGREGATE: Final[dict[str, Callable[[str, SQL], SQL]]] = {
    "sum": lambda table, expr: SQL("SUM(%s)", expr),
    "avg": lambda table, expr: SQL("AVG(%s)", expr),
    "max": lambda table, expr: SQL("MAX(%s)", expr),
    "min": lambda table, expr: SQL("MIN(%s)", expr),
    "bool_and": lambda table, expr: SQL("BOOL_AND(%s)", expr),
    "bool_or": lambda table, expr: SQL("BOOL_OR(%s)", expr),
    "array_agg": _array_agg,
    "array_agg_distinct": lambda table, expr: SQL(
        "(SELECT array_agg(v ORDER BY v) FROM (SELECT DISTINCT unnest(array_agg(%s)) AS v) sub)",
        expr,
    ),
    "recordset": _array_agg,
    "count": lambda table, expr: SQL("COUNT(%s)", expr),
    "count_distinct": lambda table, expr: SQL("COUNT(DISTINCT %s)", expr),
    "any_value": lambda table, expr: SQL("ANY_VALUE(%s)", expr),
}


#: the aggregate functions a non-stored compute answers by computing the field
#: over each group's records and folding in Python (read_group/sql.py
#: `_aggregates_through_records`); `recordset` and `any_value` are not among
#: them, the first being the mechanism itself
READ_GROUP_THROUGH_RECORDS: Final[frozenset[str]] = frozenset(
    {
        "sum",
        "avg",
        "min",
        "max",
        "count",
        "count_distinct",
        "array_agg",
        "array_agg_distinct",
        "bool_and",
        "bool_or",
        "sum_currency",
    }
)


READ_GROUP_DISPLAY_FORMAT: Final[dict[str, str]] = {
    "hour": "hh:00 dd MMM",
    "day": "dd MMM yyyy",
    "week": "'W'w YYYY",
    "month": "MMMM yyyy",
    "quarter": "QQQ yyyy",
    "year": "yyyy",
}
