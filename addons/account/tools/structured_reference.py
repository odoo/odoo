import re
from itertools import zip_longest

from stdnum import iso11649, luhn
from stdnum.iso7064 import mod_97_10

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

__all__ = [
    "format_structured_reference_iso",
    "is_valid_structured_reference",
    "is_valid_structured_reference_be",
    "is_valid_structured_reference_dk",
    "is_valid_structured_reference_fi",
    "is_valid_structured_reference_for_country",
    "is_valid_structured_reference_iso",
    "is_valid_structured_reference_nl",
    "is_valid_structured_reference_no_se",
    "is_valid_structured_reference_si",
    "normalize_structured_reference",
]


def normalize_structured_reference(reference):
    ref = re.sub(r"\s", "", reference)
    if re.fullmatch(r"(\+{3}|\*{3}|)\d{3}/\d{4}/\d{5}\1", ref):
        return re.sub(r"[+*/]", "", ref)
    return ref


def format_structured_reference_iso(number):
    check_digits = mod_97_10.calc_check_digits(f"{number}RF")
    return "RF{} {}".format(
        check_digits,
        " ".join(
            "".join(x) for x in zip_longest(*[iter(str(number))] * 4, fillvalue="")
        ),
    )


def is_valid_structured_reference_iso(reference):
    ref = normalize_structured_reference(reference)
    return iso11649.is_valid(ref)


def is_valid_structured_reference_be(reference):
    ref = normalize_structured_reference(reference)
    be_ref = re.fullmatch(r"(\d{10})(\d{2})", ref)
    if not be_ref:
        return False
    check = int(be_ref.group(1)) % 97 or 97
    return check == int(be_ref.group(2))


def is_valid_structured_reference_dk(reference):
    ref = normalize_structured_reference(reference)
    match = re.fullmatch(r"\+?(?:71<(\d{15})|75<(\d{16}))\+\d{8}<", ref)
    if not match:
        return False

    payment_ref = match.group(1) or match.group(2)
    return luhn.is_valid(payment_ref)


def is_valid_structured_reference_fi(reference):
    ref = normalize_structured_reference(reference)
    fi_ref = re.fullmatch(r"(\d{1,19})(\d)", ref)
    if not fi_ref:
        return False
    total = sum(
        (7, 3, 1)[idx % 3] * int(val) for idx, val in enumerate(fi_ref.group(1)[::-1])
    )
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(fi_ref.group(2))


def is_valid_structured_reference_no_se(reference):
    ref = normalize_structured_reference(reference)
    no_se_ref = re.fullmatch(r"\d+", ref)
    return no_se_ref and luhn.is_valid(ref)


def is_valid_structured_reference_nl(reference):
    sanitized_reference = normalize_structured_reference(reference)

    if re.fullmatch(r"\d{7}", sanitized_reference):
        _debug.logic("nl_short_reference_accepted", length=7)
        return True

    if not re.fullmatch(r"\d{9,16}", sanitized_reference):
        _debug.logic("nl_digits_rejected", reason="not_9_to_16_digits")
        return False

    if len(sanitized_reference) == 15:
        _debug.logic("nl_length_rejected", reason="length_15")
        return False

    check, reference_to_check = sanitized_reference[0], sanitized_reference[1:]
    weigths = [2, 4, 8, 5, 10, 9, 7, 3, 6, 1]
    reference_to_check = reference_to_check.zfill(16)[::-1]

    total = sum(
        int(digit) * weigths[index % len(weigths)]
        for index, digit in enumerate(reference_to_check)
    )
    computed_check = 11 - (total % 11)
    if computed_check == 11:
        computed_check = 0
    elif computed_check == 10:
        computed_check = 1

    _debug.logic("nl_check_digit_compared", computed=computed_check, given=check)
    return computed_check == int(check)


def is_valid_structured_reference_si(reference):
    sanitized_reference = normalize_structured_reference(reference)

    if sanitized_reference.startswith("SI01"):
        sanitized_reference = sanitized_reference[4:]
    else:
        _debug.logic("si_prefix_rejected", reason="prefix")
        return False

    if sanitized_reference.count("-") > 2:
        return False

    match = re.match(r"^(\d+)-(\d+)-(\d+)$", sanitized_reference)
    if not match:
        _debug.logic("si_shape_rejected", reason="groups")
        return False

    core = sanitized_reference.replace("-", "")
    if not core.isdigit() or len(core) < 2:
        return False

    digits, given_check_digit = core[:-1], core[-1]

    weights = list(range(2, 14))
    weights = weights[0 : len(digits)]
    weighted_sum = sum(
        int(d) * w for d, w in zip(reversed(digits), weights, strict=False)
    )

    expected_check_digit = 11 - (weighted_sum % 11)
    if expected_check_digit in (10, 11):
        expected_check_digit = 0

    _debug.logic(
        "si_check_digit_compared",
        given=given_check_digit,
        expected=expected_check_digit,
    )
    return given_check_digit == str(expected_check_digit)


def is_valid_structured_reference(reference):
    reference = normalize_structured_reference(reference or "")

    return (
        (
            is_valid_structured_reference_be(reference)
            or is_valid_structured_reference_dk(reference)
            or is_valid_structured_reference_fi(reference)
            or is_valid_structured_reference_no_se(reference)
            or is_valid_structured_reference_si(reference)
            or is_valid_structured_reference_nl(reference)
            or is_valid_structured_reference_iso(reference)
        )
        if reference
        else False
    )


def is_valid_structured_reference_for_country(reference, country_code=""):
    check_per_country = {
        "BE": is_valid_structured_reference_be,
        "FI": is_valid_structured_reference_fi,
        "NO": is_valid_structured_reference_no_se,
        "SE": is_valid_structured_reference_no_se,
        "NL": is_valid_structured_reference_nl,
        "SI": is_valid_structured_reference_si,
    }

    reference = normalize_structured_reference(reference or "")
    if check := check_per_country.get(country_code.upper()):
        return check(reference)
    return is_valid_structured_reference_iso(reference)
