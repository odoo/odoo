"""Odoo-agnostic date and time utilities.

Pure Python date/time helpers with no Odoo dependencies.
Uses standard library datetime, zoneinfo, and dateutil.
"""

from .date_utils import (
    # Constants
    utc,
    WEEKDAY_NUMBER,
    # Time conversion
    float_to_time,
    time_to_float,
    # Timezone handling
    localized,
    to_timezone,
    # Parsing
    parse_iso_date,
    # Period calculations
    get_month,
    get_quarter,
    get_quarter_number,
    get_fiscal_year,
    get_timedelta,
    start_of,
    end_of,
    # Arithmetic
    add,
    subtract,
    # Iteration
    date_range,
    sum_intervals,
    # Week utilities
    weeknumber,
    weekstart,
    weekend,
)

from .tz import (
    timezone,
    localize as tz_localize,
    all_timezones,
    TIMEZONE_ALIASES,
)

__all__ = [
    "TIMEZONE_ALIASES",
    "WEEKDAY_NUMBER",
    # Arithmetic
    "add",
    "all_timezones",
    # Iteration
    "date_range",
    "end_of",
    # Time conversion
    "float_to_time",
    "get_fiscal_year",
    # Period calculations
    "get_month",
    "get_quarter",
    "get_quarter_number",
    "get_timedelta",
    # Timezone handling
    "localized",
    # Parsing
    "parse_iso_date",
    "start_of",
    "subtract",
    "sum_intervals",
    "time_to_float",
    "timezone",
    "to_timezone",
    "tz_localize",
    # Constants
    "utc",
    "weekend",
    # Week utilities
    "weeknumber",
    "weekstart",
]
