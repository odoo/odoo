"""
Read Group constants for the ORM.

This module provides the read_group-specific constants: time/number granularity
mappings, aggregate functions, and display format strings. These are kept here
(rather than in primitives.py) because they depend on dateutil and have a
narrower audience than the core primitives.
"""

import dateutil.relativedelta

from odoo.tools import SQL

# =============================================================================
# Read Group Constants
# =============================================================================

# Time granularity for date grouping (returns relativedelta intervals)
READ_GROUP_TIME_GRANULARITY = {
    "hour": dateutil.relativedelta.relativedelta(hours=1),
    "day": dateutil.relativedelta.relativedelta(days=1),
    "week": dateutil.relativedelta.relativedelta(days=7),
    "month": dateutil.relativedelta.relativedelta(months=1),
    "quarter": dateutil.relativedelta.relativedelta(months=3),
    "year": dateutil.relativedelta.relativedelta(years=1),
}

# Number granularity for extracting date parts (maps to PostgreSQL date_part functions)
READ_GROUP_NUMBER_GRANULARITY = {
    "year_number": "year",
    "quarter_number": "quarter",
    "month_number": "month",
    "iso_week_number": "week",  # ISO week number because anything else than ISO is nonsense
    "day_of_year": "doy",
    "day_of_month": "day",
    "day_of_week": "dow",
    "hour_number": "hour",
    "minute_number": "minute",
    "second_number": "second",
}

# Combined time and number granularity
READ_GROUP_ALL_TIME_GRANULARITY = (
    READ_GROUP_TIME_GRANULARITY | READ_GROUP_NUMBER_GRANULARITY
)

# Valid SQL aggregation functions for read_group
READ_GROUP_AGGREGATE = {
    "sum": lambda table, expr: SQL("SUM(%s)", expr),
    "avg": lambda table, expr: SQL("AVG(%s)", expr),
    "max": lambda table, expr: SQL("MAX(%s)", expr),
    "min": lambda table, expr: SQL("MIN(%s)", expr),
    "bool_and": lambda table, expr: SQL("BOOL_AND(%s)", expr),
    "bool_or": lambda table, expr: SQL("BOOL_OR(%s)", expr),
    "array_agg": lambda table, expr: SQL(
        "ARRAY_AGG(%s ORDER BY %s)", expr, SQL.identifier(table, "id")
    ),
    "array_agg_distinct": lambda table, expr: SQL(
        "(SELECT array_agg(v ORDER BY v) FROM (SELECT DISTINCT unnest(array_agg(%s)) AS v) sub)",
        expr,
    ),
    # 'recordset' aggregates will be post-processed to become recordsets
    "recordset": lambda table, expr: SQL(
        "ARRAY_AGG(%s ORDER BY %s)", expr, SQL.identifier(table, "id")
    ),
    "count": lambda table, expr: SQL("COUNT(%s)", expr),
    "count_distinct": lambda table, expr: SQL("COUNT(DISTINCT %s)", expr),
    # any_value (PG16+): returns an arbitrary non-null value from the group.
    # Useful for fields that are functionally dependent on the GROUP BY columns
    # (e.g., partner name when grouping by partner_id) without adding them
    # to GROUP BY or using a heavier aggregate like MIN/MAX.
    "any_value": lambda table, expr: SQL("ANY_VALUE(%s)", expr),
}

# Display formats for read_group date groupings (Babel format strings)
# Careful with week/year formats:
#  - yyyy (lower) must always be used, *except* for week+year formats
#  - YYYY (upper) must always be used for week+year format
#         e.g. 2006-01-01 is W52 2005 in some locales (de_DE),
#                         and W1 2006 for others
#
# Mixing both formats, e.g. 'MMM YYYY' would yield wrong results,
# such as 2006-01-01 being formatted as "January 2005" in some locales.
# Cfr: http://babel.pocoo.org/en/latest/dates.html#date-fields
READ_GROUP_DISPLAY_FORMAT = {
    "hour": "hh:00 dd MMM",
    "day": "dd MMM yyyy",  # yyyy = normal year
    "week": "'W'w YYYY",  # w YYYY = ISO week-year
    "month": "MMMM yyyy",
    "quarter": "QQQ yyyy",
    "year": "yyyy",
}
