"""
Date, time, and number formatting utilities for Odoo.
"""

import datetime
import re
import typing

import babel.dates

from odoo.libs.datetime import utc
from odoo.libs.datetime.tz import timezone as get_timezone
from odoo.libs.locale import posix_to_ldml
from odoo.libs.numbers.float_utils import float_round

from .locale_utils import babel_locale_parse, get_lang

if typing.TYPE_CHECKING:
    from odoo.api import Environment

NON_BREAKING_SPACE = "\N{NO-BREAK SPACE}"

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = (
    f"{DEFAULT_SERVER_DATE_FORMAT} {DEFAULT_SERVER_TIME_FORMAT}"
)

DATE_LENGTH = len(datetime.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))

# Python's strftime supports only the format directives
# that are available on the platform's libc, so in order to
# be cross-platform we map to the directives required by
# the C standard (1989 version), always available on platforms
# with a C standard implementation.
DATETIME_FORMATS_MAP = {
    "%C": "",  # century
    "%D": "%m/%d/%Y",  # modified %y->%Y
    "%e": "%d",
    "%E": "",  # special modifier
    "%F": "%Y-%m-%d",
    "%g": "%Y",  # modified %y->%Y
    "%G": "%Y",
    "%h": "%b",
    "%k": "%H",
    "%l": "%I",
    "%n": "\n",
    "%O": "",  # special modifier
    "%P": "%p",
    "%R": "%H:%M",
    "%r": "%I:%M:%S %p",
    "%s": "",  # num of seconds since epoch
    "%T": "%H:%M:%S",
    "%t": " ",  # tab
    "%u": " %w",
    "%V": "%W",
    "%y": "%Y",  # Even if %y works, it's ambiguous, so we should use %Y
    "%+": "%Y-%m-%d %H:%M:%S",
    # %Z is a special case that causes 2 problems at least:
    #  - the timezone names we use (in res_user.context_tz) come
    #    from IANA/zoneinfo, but not all these names are recognized by
    #    strptime(), so we cannot convert in both directions
    #    when such a timezone is selected and %Z is in the format
    #  - %Z is replaced by an empty string in strftime() when
    #    there is not tzinfo in a datetime value (e.g when the user
    #    did not pick a context_tz). The resulting string does not
    #    parse back if the format requires %Z.
    # As a consequence, we strip it completely from format strings.
    # The user can always have a look at the context_tz in
    # preferences to check the timezone.
    "%z": "",
    "%Z": "",
}


def formatLang(
    env: Environment,
    value: float | typing.Literal[""],
    digits: int = 2,
    grouping: bool = True,
    dp: str | None = None,
    currency_obj: typing.Any | None = None,
    rounding_method: typing.Literal[
        "HALF-UP", "HALF-DOWN", "HALF-EVEN", "UP", "DOWN"
    ] = "HALF-EVEN",
    rounding_unit: typing.Literal[
        "decimals", "units", "thousands", "lakhs", "millions"
    ] = "decimals",
) -> str:
    """
    This function will format a number `value` to the appropriate format of the language used.

    :param env: The environment.
    :param value: The value to be formatted.
    :param digits: The number of decimals digits.
    :param grouping: Usage of language grouping or not.
    :param dp: Name of the decimals precision to be used. This will override ``digits``
                   and ``currency_obj`` precision.
    :param currency_obj: Currency to be used. This will override ``digits`` precision.
    :param rounding_method: The rounding method to be used:
        **'HALF-UP'** will round to the closest number with ties going away from zero,
        **'HALF-DOWN'** will round to the closest number with ties going towards zero,
        **'HALF_EVEN'** will round to the closest number with ties going to the closest
        even number,
        **'UP'** will always round away from 0,
        **'DOWN'** will always round towards 0.
    :param rounding_unit: The rounding unit to be used:
        **decimals** will round to decimals with ``digits`` or ``dp`` precision,
        **units** will round to units without any decimals,
        **thousands** will round to thousands without any decimals,
        **lakhs** will round to lakhs without any decimals,
        **millions** will round to millions without any decimals.

    :returns: The value formatted.
    """
    # We don't want to return 0
    if value == "":
        return ""

    if rounding_unit == "decimals":
        if dp:
            digits = env["decimal.precision"].precision_get(dp)
        elif currency_obj:
            digits = currency_obj.decimal_places
    else:
        digits = 0

    rounding_unit_mapping = {
        "decimals": 1,
        "thousands": 10**3,
        "lakhs": 10**5,
        "millions": 10**6,
        "units": 1,
    }

    value /= rounding_unit_mapping[rounding_unit]

    rounded_value = float_round(
        value, precision_digits=digits, rounding_method=rounding_method
    )
    lang = env["res.lang"].browse(get_lang(env).id)
    formatted_value = lang.format(f"%.{digits}f", rounded_value, grouping=grouping)

    if currency_obj and currency_obj.symbol:
        arguments = (formatted_value, NON_BREAKING_SPACE, currency_obj.symbol)

        return "%s%s%s" % (
            arguments if currency_obj.position == "after" else arguments[::-1]
        )

    return formatted_value


def format_date(
    env: Environment,
    value: datetime.datetime | datetime.date | str,
    lang_code: str | None = None,
    date_format: str | typing.Literal[False] = False,
) -> str:
    """
    Formats the date in a given format.

    :param env: an environment.
    :param date, datetime or string value: the date to format.
    :param string lang_code: the lang code, if not specified it is extracted from the
        environment context.
    :param string date_format: the format or the date (LDML format), if not specified the
        default format of the lang.
    :return: date formatted in the specified format.
    :rtype: string
    """
    if not value:
        return ""
    from odoo.fields import Datetime

    if isinstance(value, str):
        if len(value) < DATE_LENGTH:
            return ""
        if len(value) > DATE_LENGTH:
            # a datetime, convert to correct timezone
            value = Datetime.from_string(value)
            value = Datetime.context_timestamp(env["res.lang"], value)
        else:
            value = Datetime.from_string(value)
    elif isinstance(value, datetime.datetime) and not value.tzinfo:
        # a datetime, convert to correct timezone
        value = Datetime.context_timestamp(env["res.lang"], value)

    lang = get_lang(env, lang_code)
    locale = babel_locale_parse(lang.code)
    if not date_format:
        date_format = posix_to_ldml(lang.date_format, locale=locale)

    assert isinstance(value, datetime.date)  # datetime is a subclass of date
    return babel.dates.format_date(value, format=date_format, locale=locale)


def parse_date(
    env: Environment, value: str, lang_code: str | None = None
) -> datetime.date | str:
    """
    Parse the date from a given format. If it is not a valid format for the
    localization, return the original string.

    :param env: an environment.
    :param string value: the date to parse.
    :param string lang_code: the lang code, if not specified it is extracted from the
        environment context.
    :return: date object from the localized string
    :rtype: datetime.date
    """
    lang = get_lang(env, lang_code)
    locale = babel_locale_parse(lang.code)
    try:
        return babel.dates.parse_date(value, locale=locale)
    except:
        return value


def format_datetime(
    env: Environment,
    value: datetime.datetime | str,
    tz: str | typing.Literal[False] = False,
    dt_format: str = "medium",
    lang_code: str | None = None,
) -> str:
    """Formats the datetime in a given format.

    :param env:
    :param str|datetime value: naive datetime to format either in string or in datetime
    :param str tz: name of the timezone  in which the given datetime should be localized
    :param str dt_format: one of "full", "long", "medium", or "short", or a custom date/time pattern compatible with `babel` lib
    :param str lang_code: ISO code of the language to use to render the given datetime
    :rtype: str
    """
    if not value:
        return ""
    if isinstance(value, str):
        from odoo.fields import Datetime

        timestamp = Datetime.from_string(value)
    else:
        timestamp = value

    tz_name = tz or env.user.tz or "UTC"
    utc_datetime = timestamp.replace(tzinfo=utc)
    try:
        context_tz = get_timezone(tz_name)
        localized_datetime = utc_datetime.astimezone(context_tz)
    except Exception:
        localized_datetime = utc_datetime

    lang = get_lang(env, lang_code)

    locale = babel_locale_parse(
        lang.code or lang_code
    )  # lang can be inactive, so `lang`is empty
    if not dt_format or dt_format == "medium":
        date_format = posix_to_ldml(lang.date_format, locale=locale)
        time_format = posix_to_ldml(lang.time_format, locale=locale)
        dt_format = f"{date_format} {time_format}"

    # Babel allows to format datetime in a specific language without change locale
    # So month 1 = January in English, and janvier in French
    # Be aware that the default value for format is 'medium', instead of 'short'
    #     medium:  Jan 5, 2016, 10:20:31 PM |   5 janv. 2016 22:20:31
    #     short:   1/5/16, 10:20 PM         |   5/01/16 22:20
    # Formatting available here : http://babel.pocoo.org/en/latest/dates.html#date-fields
    return babel.dates.format_datetime(localized_datetime, dt_format, locale=locale)


def format_time(
    env: Environment,
    value: datetime.time | datetime.datetime | str,
    tz: str | typing.Literal[False] = False,
    time_format: str = "medium",
    lang_code: str | None = None,
) -> str:
    """Format the given time (hour, minute and second) with the current user preference (language, format, ...)

    :param env:
    :param value: the time to format
    :type value: `datetime.time` instance. Could be timezoned to display tzinfo according to format (e.i.: 'full' format)
    :param tz: name of the timezone  in which the given datetime should be localized
    :param time_format: one of "full", "long", "medium", or "short", or a custom time pattern
    :param lang_code: ISO

    :rtype str
    """
    if not value:
        return ""

    if isinstance(value, datetime.time):
        localized_time = value
    else:
        if isinstance(value, str):
            from odoo.fields import Datetime

            value = Datetime.from_string(value)
        assert isinstance(value, datetime.datetime)
        tz_name = tz or env.user.tz or "UTC"
        utc_datetime = value.replace(tzinfo=utc)
        try:
            context_tz = get_timezone(tz_name)
            localized_time = utc_datetime.astimezone(context_tz).timetz()
        except Exception:
            localized_time = utc_datetime.timetz()

    lang = get_lang(env, lang_code)
    locale = babel_locale_parse(lang.code)
    if not time_format or time_format == "medium":
        time_format = posix_to_ldml(lang.time_format, locale=locale)

    return babel.dates.format_time(localized_time, format=time_format, locale=locale)


def _format_time_ago(
    env: Environment,
    time_delta: datetime.timedelta,
    lang_code: str | None = None,
    add_direction: bool = True,
) -> str:
    if not lang_code:
        langs: list[str] = [code for code, _ in env["res.lang"].get_installed()]
        if (ctx_lang := env.context.get("lang")) in langs:
            lang_code = ctx_lang
        else:
            lang_code = env.user.company_id.partner_id.lang or langs[0]
        assert isinstance(lang_code, str)
    locale = babel_locale_parse(lang_code)
    return babel.dates.format_timedelta(
        -time_delta, add_direction=add_direction, locale=locale
    )


def format_decimalized_number(number: float, decimal: int = 1) -> str:
    """Format a number to display to nearest metrics unit next to it.

    Do not display digits if all visible digits are null.
    Do not display units higher then "Tera" because most people don't know what
    a "Yotta" is.

    ::

        >>> format_decimalized_number(123_456.789)
        123.5k
        >>> format_decimalized_number(123_000.789)
        123k
        >>> format_decimalized_number(-123_456.789)
        -123.5k
        >>> format_decimalized_number(0.789)
        0.8
    """
    for unit in ["", "k", "M", "G"]:
        if abs(number) < 1000.0:
            return f"{round(number, decimal):g}{unit}"
        number /= 1000.0
    return f"{round(number, decimal):g}T"


def format_decimalized_amount(amount: float, currency: typing.Any = None) -> str:
    """Format an amount to display the currency and also display the metric unit
    of the amount.

    ::

        >>> format_decimalized_amount(123_456.789, env.ref("base.USD"))
        $123.5k
    """
    formated_amount = format_decimalized_number(amount)

    if not currency:
        return formated_amount

    if currency.position == "before":
        return f"{currency.symbol or ''}{formated_amount}"

    return f"{formated_amount} {currency.symbol or ''}"


def format_amount(
    env: Environment,
    amount: float,
    currency: typing.Any,
    lang_code: str | None = None,
    trailing_zeroes: bool = True,
) -> str:
    fmt = f"%.{currency.decimal_places}f"
    lang = env["res.lang"].browse(get_lang(env, lang_code).id)

    formatted_amount = (
        lang.format(fmt, currency.round(amount), grouping=True)
        .replace(r" ", "\N{NO-BREAK SPACE}")
        .replace(r"-", "-\N{ZERO WIDTH NO-BREAK SPACE}")
    )

    if not trailing_zeroes:
        formatted_amount = re.sub(
            rf"{re.escape(lang.decimal_point)}?0+$", "", formatted_amount
        )

    pre = post = ""
    if currency.position == "before":
        pre = f"{currency.symbol or ''}\N{NO-BREAK SPACE}"
    else:
        post = f"\N{NO-BREAK SPACE}{currency.symbol or ''}"

    return f"{pre}{formatted_amount}{post}"


def format_duration(value: float) -> str:
    """Format a float: used to display integral or fractional values as
    human-readable time spans (e.g. 1.5 as "01:30").
    """
    hours, minutes = divmod(abs(value) * 60, 60)
    minutes = round(minutes)
    if minutes == 60:
        minutes = 0
        hours += 1
    if value < 0:
        return "-%02d:%02d" % (hours, minutes)
    return "%02d:%02d" % (hours, minutes)
