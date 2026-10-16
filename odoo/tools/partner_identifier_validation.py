import re
from stdnum.at import tin as at_tin
from stdnum.exceptions import InvalidChecksum, InvalidFormat
from odoo.tools import single_email_re

NON_DIGIT_RE = re.compile(r'\D')
# KVK: 8-digit
NL_KVK_RE = re.compile(r'\d{8}')
# OIN: 20-digit
NL_OIN_RE = re.compile(r'\d{20}')
# TH Branch Code: 5-digit
TH_BRANCH_CODE_RE = re.compile(r'\d{5}')
# AT TIN: 9-digit
AT_TIN_RE = re.compile(r'\d{9}')


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


def th_branch_code_validate(value):
    """Validate a Thai branch code (exactly 5 digits)."""
    if not TH_BRANCH_CODE_RE.fullmatch(value):
        raise InvalidFormat()
    return value


def validate_email(value):
    if not single_email_re.match(value):
        raise InvalidFormat()
    return value


def at_tin_validate(number):
    """Check if the number is a valid tax identification number.
    This checks the length (9 digits) and the verification digit.
    We have to use this instead of stdnum.at tin validate because
    it tries to import another one. (Can't open orphan path)"""
    number = at_tin.compact(number)
    if not AT_TIN_RE.fullmatch(number):
        raise InvalidFormat()
    s = at_tin.calc_check_digit(number)
    if s != number[-1]:
        raise InvalidChecksum()
    return number
