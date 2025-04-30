# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time
from pytz import UTC


def product_feed_format_price(price, currency):
    return f'{currency.round(price)} {currency.name}'


def product_feed_format_date(dt):
    return UTC.localize(dt).isoformat(timespec='minutes')


def format_sale_price_effective_date(start_date, end_date, format="google"):
    """
    Returns sale price effective date range string for Google or Meta format.

    - Google format: 2024-01-01T00:00:00/2024-01-07T23:59:59
    - Meta format: ISO 8601 datetime with timezones: 2024-01-01T00:00:00+00:00/...

    :param start_date: datetime.date
    :param end_date: datetime.date
    :param format: 'google' or 'meta'
    :return: formatted string or None
    """
    if format == "meta":
        start = UTC.localize(datetime.combine(start_date, time.min)).isoformat()
        end = UTC.localize(datetime.combine(end_date, time.max.replace(second=0))).isoformat()
        return f"{start}/{end}"

    # Google format
    return "/".join(map(product_feed_format_date, (start_date, end_date)))
