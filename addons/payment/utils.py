# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac

from odoo.tools import consteq, float_round, ustr


# Access token management

def generate_access_token(secret, *values):
    """ Generate an access token based on the provided values.

    The token allows to later verify the validity of a request, based on a given set of values.
    These will generally include the partner id, amount, currency id, transaction id or transaction
    reference. All values must be convertible to a string.

    :param str secret: The secret string to use to sign the token
    :param list values: The values to use for the generation of the token
    :return: The generated access token
    :rtype: str
    """
    token_str = ''.join(str(val) for val in values)
    access_token = hmac.new(
        secret.encode('utf-8'), token_str.encode('utf-8'), hashlib.sha256
    ).hexdigest()
    return access_token


def check_access_token(access_token, secret, *values):
    """ Check the validity of the access token for the provided values.

    The values must be provided in the exact same order as they were to `generate_access_token`.
    All values must be convertible to a string.

    :param str access_token: The access token used to verify the provided values
    :param str secret: The secret string used to sign the token
    :param list values: The values to verify against the token
    :return: True if the check is successful
    :rtype: bool
    """
    authentic_token = generate_access_token(secret, *values)
    return access_token and consteq(ustr(access_token), authentic_token)


# Transaction context formatting

def convert_to_minor_units(base_amount, currency, arbitrary_decimal_number=None):
    """ Return the amount converted to the minor units of its currency.

    The conversion is done by multiplying the base amount by 10^k where k is the number of decimals
    of the currency as per the ISO 4217 norm.
    To force a different number of decimals, set it as the value of the `decimal_number` argument.

    :param float base_amount: The amount to convert
    :param recordset currency: The currency of the amount, as a `res.currency` record
    :param int arbitrary_decimal_number: The number of decimals to use instead of that of ISO 4217
    :return: The amount in minor units of its currency
    :rtype: int
    """
    currency.ensure_one()

    if arbitrary_decimal_number is None:
        decimal_number = currency.decimal_places
    else:
        decimal_number = arbitrary_decimal_number
    return int(float_round(base_amount, decimal_number) * (10**decimal_number))


# Partner fields formatting

def format_partner_address(address1="", address2=""):
    """ Format a two-parts partner address into a one-line address string.

    :param str address1: The first part of the address, usually the `street1` field
    :param str address2: The second part of the address, usually the `street2` field
    :return: The formatted one-line address
    :rtype: str
    """
    return f"{address1} {address2}".strip()


def split_partner_name(partner_name):
    """ Split a single-line partner name in a tuple of first name, last name.

    :param str partner_name: The partner name
    :return: The splitted first name and last name
    :rtype: tuple
    """
    return " ".join(partner_name.split()[:-1]), partner_name.split()[-1]
