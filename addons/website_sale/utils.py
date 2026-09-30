# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import UTC


def gmc_format_price(price, currency):
    return f'{currency.round(price)} {currency.name}'

def gmc_format_date(dt):
    return UTC.localize(dt).isoformat(timespec='minutes')
