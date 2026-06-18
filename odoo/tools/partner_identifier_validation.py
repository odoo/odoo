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

    Also accepts the 'SGUEN' + UEN form, under which the SGNIC SMP registers
    Singapore participants for Peppol scheme 0195.
    """
    try:
        return sg_uen.validate(value)
    except ValidationError:
        if value[:5].upper() != 'SGUEN':
            raise
        return 'SGUEN' + sg_uen.validate(value[5:])


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
