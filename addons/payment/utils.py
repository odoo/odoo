# Part of Odoo. See LICENSE file for full copyright and licensing details.

from hashlib import sha1

from odoo import fields
from odoo.http import request
from odoo.tools import consteq, float_round, ustr
from odoo.tools.misc import hmac as hmac_tool


# Access token management

def generate_access_token(*values):
    """ Generate an access token based on the provided values.

    The token allows to later verify the validity of a request, based on a given set of values.
    These will generally include the partner id, amount, currency id, transaction id or transaction
    reference.
    All values must be convertible to a string.

    :param list values: The values to use for the generation of the token
    :return: The generated access token
    :rtype: str
    """
    token_str = '|'.join(str(val) for val in values)
    access_token = hmac_tool(request.env(su=True), 'generate_access_token', token_str)
    return access_token


def check_access_token(access_token, *values):
    """ Check the validity of the access token for the provided values.

    The values must be provided in the exact same order as they were to `generate_access_token`.
    All values must be convertible to a string.

    :param str access_token: The access token used to verify the provided values
    :param list values: The values to verify against the token
    :return: True if the check is successful
    :rtype: bool
    """
    authentic_token = generate_access_token(*values)
    return access_token and consteq(ustr(access_token), authentic_token)


# Transaction values formatting

def singularize_reference_prefix(prefix='tx', separator='-', max_length=None):
    """ Make the prefix more unique by suffixing it with the current datetime.

    When the prefix is a placeholder that would be part of a large sequence of references sharing
    the same prefix, such as "tx" or "validation", singularizing it allows to make it part of a
    single-element sequence of transactions. The computation of the full reference will then execute
    faster by failing to find existing references with a matching prefix.

    If the `max_length` argument is passed, the end of the prefix can be stripped before
    singularizing to ensure that the result accounts for no more than `max_length` characters.

    :param str prefix: The custom prefix to singularize
    :param str separator: The custom separator used to separate the prefix from the suffix
    :param int max_length: The maximum length of the singularized prefix
    :return: The singularized prefix
    :rtype: str
    """
    if prefix is None:
        prefix = 'tx'
    if max_length:
        DATETIME_LENGTH = 14
        assert max_length >= 1 + len(separator) + DATETIME_LENGTH  # 1 char + separator + datetime
        prefix = prefix[:max_length-len(separator)-DATETIME_LENGTH]
    return f'{prefix}{separator}{fields.Datetime.now().strftime("%Y%m%d%H%M%S")}'


def to_major_currency_units(minor_amount, currency, arbitrary_decimal_number=None):
    """ Return the amount converted to the major units of its currency.

    The conversion is done by dividing the amount by 10^k where k is the number of decimals of the
    currency as per the ISO 4217 norm.
    To force a different number of decimals, set it as the value of the `arbitrary_decimal_number`
    argument.

    :param float minor_amount: The amount in minor units, to convert in major units
    :param recordset currency: The currency of the amount, as a `res.currency` record
    :param int arbitrary_decimal_number: The number of decimals to use instead of that of ISO 4217
    :return: The amount in major units of its currency
    :rtype: int
    """
    currency.ensure_one()

    if arbitrary_decimal_number is None:
        decimal_number = currency.decimal_places
    else:
        decimal_number = arbitrary_decimal_number
    return float_round(minor_amount, precision_digits=0) / (10**decimal_number)


def to_minor_currency_units(major_amount, currency, arbitrary_decimal_number=None):
    """ Return the amount converted to the minor units of its currency.

    The conversion is done by multiplying the amount by 10^k where k is the number of decimals of
    the currency as per the ISO 4217 norm.
    To force a different number of decimals, set it as the value of the `arbitrary_decimal_number`
    argument.

    Note: currency.ensure_one() if arbitrary_decimal_number is not provided

    :param float major_amount: The amount in major units, to convert in minor units
    :param recordset currency: The currency of the amount, as a `res.currency` record
    :param int arbitrary_decimal_number: The number of decimals to use instead of that of ISO 4217
    :return: The amount in minor units of its currency
    :rtype: int
    """
    if arbitrary_decimal_number is not None:
        decimal_number = arbitrary_decimal_number
    else:
        currency.ensure_one()
        decimal_number = currency.decimal_places
    return int(float_round(major_amount * (10**decimal_number), precision_digits=0))


# Token values formatting

def build_token_name(payment_details_short=None, final_length=16):
    """ Pad plain payment details with leading X's to build a token name of the desired length.

    :param str payment_details_short: The plain part of the payment details (usually last 4 digits)
    :param int final_length: The desired final length of the token name (16 for a bank card)
    :return: The padded token name
    :rtype: str
    """
    payment_details_short = payment_details_short or '????'
    return f"{'X' * (final_length - len(payment_details_short))}{payment_details_short}"


# Partner values formatting

def format_partner_address(address1="", address2=""):
    """ Format a two-parts partner address into a one-line address string.

    :param str address1: The first part of the address, usually the `street1` field
    :param str address2: The second part of the address, usually the `street2` field
    :return: The formatted one-line address
    :rtype: str
    """
    address1 = address1 or ""  # Avoid casting as "False"
    address2 = address2 or ""  # Avoid casting as "False"
    return f"{address1} {address2}".strip()


def split_partner_name(partner_name):
    """ Split a single-line partner name in a tuple of first name, last name.

    :param str partner_name: The partner name
    :return: The splitted first name and last name
    :rtype: tuple
    """
    return " ".join(partner_name.split()[:-1]), partner_name.split()[-1]


# Security

def get_customer_ip_address():
    return request and request.httprequest.remote_addr or ''


def check_rights_on_recordset(recordset):
    """ Ensure that the user has the rights to write on the record.

    Call this method to check the access rules and rights before doing any operation that is
    callable by RPC and that requires to be executed in sudo mode.

    :param recordset: The recordset for which the rights should be checked.
    :return: None
    """
    recordset.check_access_rights('write')
    recordset.check_access_rule('write')


# Idempotency

def generate_idempotency_key(tx, scope=None):
    """ Generate an idempotency key for the provided transaction and scope.

    Idempotency keys are used to prevent API requests from going through twice in a short time: the
    API rejects requests made after another one with the same payload and idempotency key if it
    succeeded.

    The idempotency key is generated based on the transaction reference, database UUID, and scope if
    any. This guarantees the key is identical for two API requests with the same transaction
    reference, database, and endpoint. Should one of these parameters differ, the key is unique from
    one request to another (e.g., after dropping the database, for different endpoints, etc.).

    :param recordset tx: The transaction to generate an idempotency key for, as a
                         `payment.transaction` record.
    :param str scope: The scope of the API request to generate an idempotency key for. This should
                      typically be the API endpoint. It is not necessary to provide the scope if the
                      API takes care of comparing idempotency keys per endpoint.
    :return: The generated idempotency key.
    :rtype: str
    """
    database_uuid = tx.env['ir.config_parameter'].sudo().get_param('database.uuid')
    return sha1(f'{database_uuid}{tx.reference}{scope or ""}'.encode()).hexdigest()
