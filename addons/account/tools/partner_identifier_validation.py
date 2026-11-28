import re

from stdnum.at import businessid as at_businessid
from stdnum.at import uid as at_uid
from stdnum.exceptions import InvalidFormat, ValidationError

NON_DIGIT_RE = re.compile(r'\D')
# KVK: 8-digit
NL_KVK_RE = re.compile(r'\d{8}')
# OIN: 20-digit
NL_OIN_RE = re.compile(r'\d{20}')


# ===========================================================
# Validators when no library provides it (typically stdnum) =
# ===========================================================
def nl_kvk_validate(value):
    """Normalize and validate a Dutch KVK number."""
    value = NON_DIGIT_RE.sub('', value)
    if not NL_KVK_RE.fullmatch(value):
        raise InvalidFormat()
    return value


def nl_oin_validate(value):
    """Normalize and validate a Dutch OIN."""
    value = NON_DIGIT_RE.sub('', value)
    if not NL_OIN_RE.fullmatch(value):
        raise InvalidFormat()
    return value


def at_en_validate(number):
    """Austrian Firmenbuchnummer. UID values are still accepted because AT_EN used to be
    deduced from the VAT (and migrated from company_registry with the UID validator).
    TODO master: drop the UID fallback + upgrade script removing UID-shaped AT_EN values."""
    try:
        return at_businessid.validate(number.lower())
    except ValidationError:
        if at_uid.is_valid(number):
            return at_uid.compact(number)  # 'ATU12345675' -> 'U12345675', same as before
        raise
