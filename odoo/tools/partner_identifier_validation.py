import re
from stdnum.exceptions import InvalidFormat, ValidationError
from stdnum.sg import uen as sg_uen
from odoo.tools import single_email_re

NON_DIGIT_RE = re.compile(r'\D')
# KVK: 8-digit
NL_KVK_RE = re.compile(r'\d{8}')
# OIN: 20-digit
NL_OIN_RE = re.compile(r'\d{20}')
# TH Branch Code: 5-digit
TH_BRANCH_CODE_RE = re.compile(r'\d{5}')
# PK Consumer Identification: 13-digit CNIC
PK_CN_RE = re.compile(r'\d{13}')
# Prefixes of the Peppol scheme 0195 participant identifiers wrapping a Singapore UEN:
# 'SGUEN' for businesses, 'SGUXN' for government bodies.
SG_PEPPOL_UEN_PREFIXES = ('SGUEN', 'SGUXN')
# Prefixes of the remaining scheme 0195 participant identifiers, whose remainder is not a
# UEN: 'SGTST'/'SGGST' identify test participants, and 'XXUID' is a universal identifier
# where 'XX' is an ISO 3166-1 alpha-2 country code (e.g. 'FRUID' for France).
SG_PEPPOL_OTHER_PREFIX_RE = re.compile(r'SGTST|SGGST|[A-Z]{2}UID')


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
        if prefix in SG_PEPPOL_UEN_PREFIXES:
            return prefix + sg_uen.validate(remainder)
        if remainder and SG_PEPPOL_OTHER_PREFIX_RE.fullmatch(prefix):
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
