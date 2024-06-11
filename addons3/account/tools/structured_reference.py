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
    check_digits = mod_97_10.calc_check_digits('{}RF'.format(number))
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
    be_ref = re.match(r'(\d{10})(\d{2})', ref)
    return be_ref and int(be_ref.group(1)) % 97 == int(be_ref.group(2)) % 97

def is_valid_structured_reference_fi(reference):
    """Check whether the provided reference is a valid structured reference for Finland.

    :param reference: the reference to check
    """
    ref = sanitize_structured_reference(reference)
    fi_ref = re.match(r'(\d{1,19})(\d)', ref)
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
    no_se_ref = re.match(r'\d+', ref)
    return no_se_ref and luhn.is_valid(ref)
