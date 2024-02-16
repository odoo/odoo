from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Literal, Optional, Sequence

import babel
import pytz
from babel import lists

import odoo
from odoo.tools import float_round

if TYPE_CHECKING:
    import odoo.api

    from odoo.addons.base.models.res_lang import LangData


NON_BREAKING_SPACE = u"\N{NO-BREAK SPACE}"

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_TIME_FORMAT)
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
    #    from pytz, but not all these names are recognized by
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

POSIX_TO_LDML = {
    "a": "E",
    "A": "EEEE",
    "b": "MMM",
    "B": "MMMM",
    #'c': '',
    "d": "dd",
    "H": "HH",
    "I": "hh",
    "j": "DDD",
    "m": "MM",
    "M": "mm",
    "p": "a",
    "S": "ss",
    "U": "w",
    "w": "e",
    "W": "w",
    "y": "yy",
    "Y": "yyyy",
    # see comments above, and babel's format_datetime assumes an UTC timezone
    # for naive datetime objects
    #'z': 'Z',
    #'Z': 'z',
}


def posix_to_ldml(fmt, locale):
    """Converts a posix/strftime pattern into an LDML date format pattern.

    :param fmt: non-extended C89/C90 strftime pattern
    :param locale: babel locale used for locale-specific conversions (e.g. %x and %X)
    :return: unicode
    """
    buf = []
    pc = False
    quoted = []

    for c in fmt:
        # LDML date format patterns uses letters, so letters must be quoted
        if not pc and c.isalpha():
            quoted.append(c if c != "'" else "''")
            continue
        if quoted:
            buf.append("'")
            buf.append("".join(quoted))
            buf.append("'")
            quoted = []

        if pc:
            if c == "%":  # escaped percent
                buf.append("%")
            elif c == "x":  # date format, short seems to match
                buf.append(locale.date_formats["short"].pattern)
            elif c == "X":  # time format, seems to include seconds. short does not
                buf.append(locale.time_formats["medium"].pattern)
            else:  # look up format char in static mapping
                buf.append(POSIX_TO_LDML[c])
            pc = False
        elif c == "%":
            pc = True
        else:
            buf.append(c)

    # flush anything remaining in quoted buffer
    if quoted:
        buf.append("'")
        buf.append("".join(quoted))
        buf.append("'")

    return "".join(buf)


def get_lang(env, lang_code=False) -> LangData:
    """
    Retrieve the first lang object installed, by checking the parameter lang_code,
    the context and then the company. If no lang is installed from those variables,
    fallback on english or on the first lang installed in the system.

    :param env:
    :param str lang_code: the locale (i.e. en_US)
    :return LangData: the first lang found that is installed on the system.
    """
    langs = [code for code, _ in env["res.lang"].get_installed()]
    lang = "en_US" if "en_US" in langs else langs[0]
    if lang_code and lang_code in langs:
        lang = lang_code
    elif (context_lang := env.context.get("lang")) in langs:
        lang = context_lang
    elif (company_lang := env.user.with_context(lang="en_US").company_id.partner_id.lang) in langs:
        lang = company_lang
    return env["res.lang"]._get_data(code=lang)


def babel_locale_parse(lang_code):
    try:
        return babel.Locale.parse(lang_code)
    except Exception:
        try:
            return babel.Locale.default()
        except Exception:
            return babel.Locale.parse("en_US")


def formatLang(
    env,
    value,
    digits=2,
    grouping=True,
    monetary=False,
    dp=None,
    currency_obj=None,
    rounding_method="HALF-EVEN",
    rounding_unit="decimals",
):
    """
    This function will format a number `value` to the appropriate format of the language used.

    :param Object env: The environment.
    :param float value: The value to be formatted.
    :param int digits: The number of decimals digits.
    :param bool grouping: Usage of language grouping or not.
    :param bool monetary: Usage of thousands separator or not.
        .. deprecated:: 13.0
    :param str dp: Name of the decimals precision to be used. This will override ``digits``
                   and ``currency_obj`` precision.
    :param Object currency_obj: Currency to be used. This will override ``digits`` precision.
    :param str rounding_method: The rounding method to be used:
        **'HALF-UP'** will round to the closest number with ties going away from zero,
        **'HALF-DOWN'** will round to the closest number with ties going towards zero,
        **'HALF_EVEN'** will round to the closest number with ties going to the closest
        even number,
        **'UP'** will always round away from 0,
        **'DOWN'** will always round towards 0.
    :param str rounding_unit: The rounding unit to be used:
        **decimals** will round to decimals with ``digits`` or ``dp`` precision,
        **units** will round to units without any decimals,
        **thousands** will round to thousands without any decimals,
        **lakhs** will round to lakhs without any decimals,
        **millions** will round to millions without any decimals.

    :returns: The value formatted.
    :rtype: str
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
    }

    value /= rounding_unit_mapping.get(rounding_unit, 1)

    rounded_value = float_round(value, precision_digits=digits, rounding_method=rounding_method)
    lang = env["res.lang"].browse(get_lang(env).id)
    formatted_value = lang.format(f"%.{digits}f", rounded_value, grouping=grouping)

    if currency_obj and currency_obj.symbol:
        arguments = (formatted_value, NON_BREAKING_SPACE, currency_obj.symbol)

        return "%s%s%s" % (arguments if currency_obj.position == "after" else arguments[::-1])

    return formatted_value


def format_date(env, value, lang_code=False, date_format=False):
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
    if isinstance(value, str):
        if len(value) < DATE_LENGTH:
            return ""
        if len(value) > DATE_LENGTH:
            # a datetime, convert to correct timezone
            value = odoo.fields.Datetime.from_string(value)
            value = odoo.fields.Datetime.context_timestamp(env["res.lang"], value)
        else:
            value = odoo.fields.Datetime.from_string(value)
    elif isinstance(value, datetime.datetime) and not value.tzinfo:
        # a datetime, convert to correct timezone
        value = odoo.fields.Datetime.context_timestamp(env["res.lang"], value)

    lang = get_lang(env, lang_code)
    locale = babel_locale_parse(lang.code)
    if not date_format:
        date_format = posix_to_ldml(lang.date_format, locale=locale)

    return babel.dates.format_date(value, format=date_format, locale=locale)


def parse_date(env, value, lang_code=False):
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
    except Exception:
        return value


def format_datetime(env, value, tz=False, dt_format="medium", lang_code=False):
    """Formats the datetime in a given format.

    :param env:
    :param str|datetime value: naive datetime to format either in string or in datetime
    :param str tz: name of the timezone  in which the given datetime should be localized
    :param str dt_format: one of “full”, “long”, “medium”, or “short”, or a custom date/time pattern compatible with `babel` lib
    :param str lang_code: ISO code of the language to use to render the given datetime
    :rtype: str
    """
    if not value:
        return ""
    if isinstance(value, str):
        timestamp = odoo.fields.Datetime.from_string(value)
    else:
        timestamp = value

    tz_name = tz or env.user.tz or "UTC"
    utc_datetime = pytz.utc.localize(timestamp, is_dst=False)
    try:
        context_tz = pytz.timezone(tz_name)
        localized_datetime = utc_datetime.astimezone(context_tz)
    except Exception:
        localized_datetime = utc_datetime

    lang = get_lang(env, lang_code)

    locale = babel_locale_parse(lang.code or lang_code)  # lang can be inactive, so `lang`is empty
    if not dt_format:
        date_format = posix_to_ldml(lang.date_format, locale=locale)
        time_format = posix_to_ldml(lang.time_format, locale=locale)
        dt_format = "%s %s" % (date_format, time_format)

    # Babel allows to format datetime in a specific language without change locale
    # So month 1 = January in English, and janvier in French
    # Be aware that the default value for format is 'medium', instead of 'short'
    #     medium:  Jan 5, 2016, 10:20:31 PM |   5 janv. 2016 22:20:31
    #     short:   1/5/16, 10:20 PM         |   5/01/16 22:20
    # Formatting available here : http://babel.pocoo.org/en/latest/dates.html#date-fields
    return babel.dates.format_datetime(localized_datetime, dt_format, locale=locale)


def format_time(env, value, tz=False, time_format="medium", lang_code=False):
    """Format the given time (hour, minute and second) with the current user preference (language, format, ...)

    :param env:
    :param value: the time to format
    :type value: `datetime.time` instance. Could be timezoned to display tzinfo according to format (e.i.: 'full' format)
    :param tz: name of the timezone  in which the given datetime should be localized
    :param time_format: one of “full”, “long”, “medium”, or “short”, or a custom time pattern
    :param lang_code: ISO

    :rtype str
    """
    if not value:
        return ""

    if isinstance(value, datetime.time):
        localized_datetime = value
    else:
        if isinstance(value, str):
            value = odoo.fields.Datetime.from_string(value)
        tz_name = tz or env.user.tz or "UTC"
        utc_datetime = pytz.utc.localize(value, is_dst=False)
        try:
            context_tz = pytz.timezone(tz_name)
            localized_datetime = utc_datetime.astimezone(context_tz)
        except Exception:
            localized_datetime = utc_datetime

    lang = get_lang(env, lang_code)
    locale = babel_locale_parse(lang.code)
    if not time_format:
        time_format = posix_to_ldml(lang.time_format, locale=locale)

    return babel.dates.format_time(localized_datetime, format=time_format, locale=locale)


def _format_time_ago(env, time_delta, lang_code=False, add_direction=True):
    if not lang_code:
        langs = [code for code, _ in env["res.lang"].get_installed()]
        lang_code = (
            env.context["lang"]
            if env.context.get("lang") in langs
            else (env.user.company_id.partner_id.lang or langs[0])
        )
    locale = babel_locale_parse(lang_code)
    return babel.dates.format_timedelta(-time_delta, add_direction=add_direction, locale=locale)


def format_decimalized_number(number, decimal=1):
    """Format a number to display to nearest metrics unit next to it.

    Do not display digits if all visible digits are null.
    Do not display units higher then "Tera" because most of people don't know what
    a "Yotta" is.

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
            return "%g%s" % (round(number, decimal), unit)
        number /= 1000.0
    return "%g%s" % (round(number, decimal), "T")


def format_decimalized_amount(amount, currency=None):
    """Format a amount to display the currency and also display the metric unit of the amount.

    >>> format_decimalized_amount(123_456.789, res.currency("$"))
    $123.5k
    """
    formated_amount = format_decimalized_number(amount)

    if not currency:
        return formated_amount

    if currency.position == "before":
        return "%s%s" % (currency.symbol or "", formated_amount)

    return "%s %s" % (formated_amount, currency.symbol or "")


def format_amount(env, amount, currency, lang_code=False):
    fmt = "%.{0}f".format(currency.decimal_places)
    lang = env["res.lang"].browse(get_lang(env, lang_code).id)

    formatted_amount = (
        lang.format(fmt, currency.round(amount), grouping=True)
        .replace(r" ", "\N{NO-BREAK SPACE}")
        .replace(r"-", "-\N{ZERO WIDTH NO-BREAK SPACE}")
    )

    pre = post = ""
    if currency.position == "before":
        pre = "{symbol}\N{NO-BREAK SPACE}".format(symbol=currency.symbol or "")
    else:
        post = "\N{NO-BREAK SPACE}{symbol}".format(symbol=currency.symbol or "")

    return "{pre}{0}{post}".format(formatted_amount, pre=pre, post=post)


def format_duration(value):
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


def format_list(
    env: odoo.api.Environment,
    lst: Sequence[str],
    style: Literal["standard", "standard-short", "or", "or-short", "unit", "unit-short", "unit-narrow"] = "standard",
    lang_code: Optional[str] = None,
) -> str:
    """
    Format the items in `lst` as a list in a locale-dependent manner with the chosen style.

    The available styles are defined by babel according to the Unicode TR35-49 spec:
    * standard:
      A typical 'and' list for arbitrary placeholders.
      e.g. "January, February, and March"
    * standard-short:
      A short version of an 'and' list, suitable for use with short or abbreviated placeholder values.
      e.g. "Jan., Feb., and Mar."
    * or:
      A typical 'or' list for arbitrary placeholders.
      e.g. "January, February, or March"
    * or-short:
      A short version of an 'or' list.
      e.g. "Jan., Feb., or Mar."
    * unit:
      A list suitable for wide units.
      e.g. "3 feet, 7 inches"
    * unit-short:
      A list suitable for short units
      e.g. "3 ft, 7 in"
    * unit-narrow:
      A list suitable for narrow units, where space on the screen is very limited.
      e.g. "3′ 7″"

    See https://www.unicode.org/reports/tr35/tr35-49/tr35-general.html#ListPatterns for more details.

    :param env: the current environment.
    :param lst: the sequence of items to format into a list.
    :param style: the style to format the list with.
    :param lang_code: the locale (e.g. en_US).
    :return: the formatted list.
    """
    locale = babel_locale_parse(lang_code or get_lang(env).code)
    # Some styles could be unavailable for the chosen locale
    if style not in locale.list_patterns:
        style = "standard"
    return lists.format_list(lst, style, locale)
