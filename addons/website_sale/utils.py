# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import UTC


def product_feed_format_price(price, currency):
    return f'{currency.round(price)} {currency.name}'


def product_feed_format_date(dt):
    return UTC.localize(dt).isoformat(timespec='minutes')


def format_sale_price_effective_date(start_date, end_date):
    """
    Returns sale price effective date range string for Google or Meta format.

    :param start_date: datetime.date
    :param end_date: datetime.date
    :return: formatted string or None
    """
    return "/".join(map(product_feed_format_date, (start_date, end_date)))
