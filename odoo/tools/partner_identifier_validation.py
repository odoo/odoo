import re
from stdnum.sg import uen as sg_uen
from stdnum.exceptions import InvalidChecksum, InvalidFormat, ValidationError
from stdnum.at import uid as at_uid
from stdnum.at import businessid as at_businessid
from stdnum.at import tin as at_steuernummer
from odoo.tools import single_email_re

NON_DIGIT_RE = re.compile(r'\D')
# AE TIN: 10-digit
AE_TIN_RE = re.compile(r'\d{10}')
# KVK: 8-digit
NL_KVK_RE = re.compile(r'\d{8}')
# OIN: 20-digit
NL_OIN_RE = re.compile(r'\d{20}')
# TH Branch Code: 5-digit
TH_BRANCH_CODE_RE = re.compile(r'\d{5}')
# PK Consumer Identification: 13-digit CNIC
PK_CN_RE = re.compile(r'\d{13}')
# Prefixes of the Peppol scheme 0195 participant identifiers: 'SGUEN'/'SGUXN' wrap a
# Singapore UEN (for businesses and government bodies respectively) and have their
# remainder validated as such; 'SGTST'/'SGGST' identify test participants and 'XXUID' is a
# universal identifier (where 'XX' is an ISO 3166-1 alpha-2 country code, e.g. 'FRUID' for
# France) whose remainder is not a UEN and is taken as-is.
SG_PEPPOL_PREFIX_RE = re.compile(r'(?P<uen_prefix>SGUEN|SGUXN)|(?P<other_prefix>SGTST|SGGST|[A-Z]{2}UID)')
# AT TIN: 9-digit
AT_TIN_RE = re.compile(r'\d{9}')


# ===========================================================
# Validators when no library provides it (typically stdnum) =
# ===========================================================
def ae_tin_validate(value):
    """Normalize and validate a UAE TIN (10 digits)."""
    value = NON_DIGIT_RE.sub('', value)
    if not AE_TIN_RE.fullmatch(value):
        raise InvalidFormat()
    return value


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


def sg_uen_validate(value):
    """Normalize and validate a Singapore UEN.

    Also accepts the prefixed forms under which the SGNIC SMP registers participants for
    Peppol scheme 0195. Only the prefixes wrapping a UEN have their remainder validated;
    the test and universal identifiers are taken as they are.
    """
    try:
        return sg_uen.validate(value)
    except ValidationError:
        prefix, remainder = value[:5].upper(), value[5:]
        match = SG_PEPPOL_PREFIX_RE.fullmatch(prefix)
        if match and match.group('uen_prefix'):
            return prefix + sg_uen.validate(remainder)
        if match and match.group('other_prefix') and remainder:
            return prefix + remainder
        raise


def th_branch_code_validate(value):
    """Validate a Thai branch code (exactly 5 digits)."""
    if not TH_BRANCH_CODE_RE.fullmatch(value):
        raise InvalidFormat()
    return value


def pk_cn_validate(value):
    """Normalize and validate a Pakistani Consumer Identification (a 13-digit CNIC)."""
    value = value.replace('-', '').replace(' ', '')
    if not PK_CN_RE.fullmatch(value):
        raise InvalidFormat()
    return f'{value[:5]}-{value[5:12]}-{value[12]}'


def validate_email(value):
    if not single_email_re.match(value):
        raise InvalidFormat()
    return value


def it_cuc_validate(value):
    value = value.strip()
    if len(value) != 8 or not value.isalnum():
        raise InvalidFormat()
    return value.upper()


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


def at_steuernummer_validate(number):
    """Check if the number is a valid tax identification number.
    This checks the length (9 digits) and the verification digit.
    We have to use this instead of stdnum.at tin validate because
    it tries to import another one. (Can't open orphan path)"""
    number = at_steuernummer.compact(number)
    if not AT_TIN_RE.fullmatch(number):
        raise InvalidFormat()
    s = at_steuernummer.calc_check_digit(number)
    if s != number[-1]:
        raise InvalidChecksum()
    return number
