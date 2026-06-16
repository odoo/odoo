import re
from stdnum.exceptions import InvalidChecksum, InvalidFormat

NON_DIGIT_RE = re.compile(r'\D')
# KVK: 8-digit
NL_KVK_RE = re.compile(r'\d{8}')
# OIN: 20-digit
NL_OIN_RE = re.compile(r'\d{20}')
# TH Branch Code: 5-digit
TH_BRANCH_CODE_RE = re.compile(r'\d{5}')
# GT CUI: 9 check-validated chars (8 digits + check digit 0-9/K) plus 0-4 admin digits
GT_CUI_RE = re.compile(r'\d{8}[\dK]\d{0,4}')


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


def gt_cui_validate(value):
    """Normalize and validate a Guatemalan CUI (Código Único de Identificación)."""
    value = re.sub(r'[\s-]', '', value)
    if not GT_CUI_RE.fullmatch(value):
        raise InvalidFormat()
    cui_sum = sum(int(d) * (i + 2) for i, d in enumerate(value[:8]))
    if value[8] != '0123456789K'[cui_sum % 11]:
        raise InvalidChecksum()
    return value


# Verification vector and helper used for both Uruguayan CI and NIE.
# Algorithms taken from Uruware's Technical Manual (sections 9.2 and 9.3).
_UY_CI_NIE_VECTOR = (2, 9, 8, 7, 6, 3, 4)


def _uy_ci_nie_validate(value, *, is_nie):
    # Normalize: strip the accepted CI/NIE formatting separators before validating.
    digits = re.sub(r"[\s.,:-]", "", value)
    if not re.fullmatch(r"\d+", digits):
        raise InvalidFormat()
    verif_digit = int(digits[-1])
    body = digits[1:-1] if is_nie else digits[:-1]
    body = "%07d" % int(body or 0)
    if len(body) > 7:
        raise InvalidFormat()
    num_sum = sum(int(body[i]) * _UY_CI_NIE_VECTOR[i] for i in range(7))
    if -num_sum % 10 != verif_digit:
        raise InvalidChecksum()
    return digits


def uy_ci_validate(value):
    """Validate a Uruguayan Cédula de Identidad number."""
    return _uy_ci_nie_validate(value, is_nie=False)


def uy_nie_validate(value):
    """Validate a Uruguayan NIE (Foreigner Identity Number)."""
    return _uy_ci_nie_validate(value, is_nie=True)
