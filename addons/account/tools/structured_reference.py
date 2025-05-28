import re

from itertools import zip_longest
from stdnum import iso11649, luhn
from stdnum.iso7064 import mod_97_10


def sanitize_structured_reference(reference):
    """Removes whitespace and specific characters from Belgian structured references:

    Example: ` RF18 1234 5678 9  ` -> `RF18123456789`
             `+++020/3430/57642+++` -> `020343057642`
             `***020/3430/57642***` -> `020343057642`
    """
    ref = re.sub(r'\s', '', reference)
    if re.match(r'(\+{3}|\*{3})\d{3}/\d{4}/\d{5}(\+{3}|\*{3})', ref):
        return re.sub(r'[+*/]', '', ref)
    return ref

def format_structured_reference_iso(number):
    """Format a string into a Structured Creditor Reference.

    The Creditor Reference is an international standard (ISO 11649).
    Example: `123456789` -> `RF18 1234 5678 9`
    """
    check_digits = mod_97_10.calc_check_digits(f"{number}RF")
    return 'RF{} {}'.format(
        check_digits,
        ' '.join(''.join(x) for x in zip_longest(*[iter(str(number))]*4, fillvalue=''))
    )

def is_valid_structured_reference_iso(reference):
    """Check whether the provided reference is a valid Structured Creditor Reference (ISO).

    :param reference: the reference to check
    """
    ref = sanitize_structured_reference(reference)
    return iso11649.is_valid(ref)

def is_valid_structured_reference_be(reference):
    """Check whether the provided reference is a valid structured reference for Belgium.

    :param reference: the reference to check
    """
    ref = sanitize_structured_reference(reference)
    be_ref = re.fullmatch(r'(\d{10})(\d{2})', ref)
    return be_ref and int(be_ref.group(1)) % 97 == int(be_ref.group(2)) % 97

def is_valid_structured_reference_fi(reference):
    """Check whether the provided reference is a valid structured reference for Finland.

    :param reference: the reference to check
    """
    ref = sanitize_structured_reference(reference)
    fi_ref = re.fullmatch(r'(\d{1,19})(\d)', ref)
    if not fi_ref:
        return False
    total = sum((7, 3, 1)[idx % 3] * int(val) for idx, val in enumerate(fi_ref.group(1)[::-1]))
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(fi_ref.group(2))

def is_valid_structured_reference_no_se(reference):
    """Check whether the provided reference is a valid structured reference for Norway or Sweden.

    :param reference: the reference to check
    """
    ref = sanitize_structured_reference(reference)
    no_se_ref = re.fullmatch(r'\d+', ref)
    return no_se_ref and luhn.is_valid(ref)


def is_valid_structured_reference_si(reference):
    """ Validates a Slovenian structured reference using Model 01 (SI01).

        Format: SI01 (P1-P2-P3)K
        - Starts with 'SI01'
        - P1, P2, P3 are numeric segments (max 20 digits total, up to 2 hyphens)
        - K is a check digit calculated using MOD 11

        :param reference: the reference to check
        :return: True if reference is a structured reference, False otherwise
    """
    sanitized_reference = sanitize_structured_reference(reference)

    if sanitized_reference.startswith('SI01'):
        sanitized_reference = sanitized_reference[4:]  # Remove SI01
    else:
        return False

    # Contains maximum of two hyphens
    if sanitized_reference.count('-') > 2:
        return False

    # Validate hyphenated parts using regex: 3 numeric parts (last ends with check digit)
    match = re.match(r'^(\d+)-(\d+)-(\d+)$', sanitized_reference)
    if not match:
        return False

    # Split into main digits and check digit
    core = sanitized_reference.replace('-', '')
    if not core.isdigit() or len(core) < 2:
        return False

    digits, given_check_digit = core[:-1], core[-1]

    weights = list(range(2, 14))
    weights = weights[0:len(digits)]
    weighted_sum = sum(int(d) * w for d, w in zip(reversed(digits), weights))

    expected_check_digit = 11 - (weighted_sum % 11)
    if expected_check_digit in (10, 11):
        expected_check_digit = 0

    return given_check_digit == str(expected_check_digit)

def is_valid_structured_reference(reference):
    """Check whether the provided reference is a valid structured reference.
    This is currently supporting SEPA enabled countries. More specifically countries covered by functions in this file.

    :param reference: the reference to check
    """
    reference = sanitize_structured_reference(reference or '')

    return (
        is_valid_structured_reference_be(reference) or
        is_valid_structured_reference_fi(reference) or
        is_valid_structured_reference_no_se(reference) or
        is_valid_structured_reference_si(reference) or
        is_valid_structured_reference_iso(reference)
    )
