import math
from decimal import Decimal
from typing import Literal

type RoundingMethod = Literal["UP", "DOWN", "HALF-UP", "HALF-DOWN", "HALF-EVEN"]

__all__ = [
    "RoundingMethod",
    "float_compare",
    "float_invert",
    "float_is_zero",
    "float_repr",
    "float_round",
    "float_split",
    "float_split_str",
    "json_float_round",
]


def _round_half_away_from_zero(f: float) -> float:
    roundf = round(f)
    if round(f + 1) - roundf != 1:
        return f + math.copysign(0.5, f)
    return math.copysign(roundf, f)


def _float_check_precision(
    precision_digits: int | None = None,
    precision_rounding: float | None = None,
) -> float:
    if precision_rounding is not None and precision_digits is None:
        if precision_rounding <= 0:
            raise ValueError(
                f"precision_rounding must be positive, got {precision_rounding}"
            )
    elif precision_digits is not None and precision_rounding is None:
        if not float(precision_digits).is_integer() or precision_digits < 0:
            raise ValueError(
                f"precision_digits must be a non-negative integer, got {precision_digits}"
            )
        precision_rounding = float(10**-precision_digits)
    else:
        msg = "exactly one of precision_digits and precision_rounding must be specified"
        raise ValueError(msg)
    return precision_rounding


def float_round(
    value: float,
    precision_digits: int | None = None,
    precision_rounding: float | None = None,
    rounding_method: RoundingMethod = "HALF-UP",
) -> float:
    return _round_r(
        value,
        _float_check_precision(precision_digits, precision_rounding),
        rounding_method,
    )


_EPSILON_SCALE = 2.0**-50


def _round_r(
    value: float,
    rounding_factor: float,
    rounding_method: RoundingMethod = "HALF-UP",
) -> float:
    if value == 0:
        return 0.0

    step = rounding_factor
    inverted = rounding_factor < 1
    if inverted:
        rounding_factor = float_invert(rounding_factor)
        normalized_value = value * rounding_factor
    else:
        normalized_value = value / rounding_factor

    if normalized_value == 0.0:  # noqa: RUF069  exact-zero fast path; 0.0 is representable
        return 0.0

    epsilon = abs(normalized_value) * _EPSILON_SCALE
    half_epsilon = max(0.0, min(epsilon, 0.5 - epsilon / 2))
    trunc_epsilon = min(epsilon, 0.5)

    if rounding_method == "HALF-UP":
        result = _round_half_away_from_zero(
            normalized_value + math.copysign(half_epsilon, normalized_value)
        )
    elif rounding_method == "HALF-EVEN":
        integral = math.floor(normalized_value)
        remainder = abs(normalized_value - integral)
        is_half = remainder == 0.5 or abs(0.5 - remainder) < half_epsilon  # noqa: RUF069  see comment above
        result = (
            integral + (integral & 1)
            if is_half
            else _round_half_away_from_zero(normalized_value)
        )
    elif rounding_method == "HALF-DOWN":
        integral = math.floor(abs(normalized_value))
        remainder = abs(normalized_value) - integral
        is_half = remainder == 0.5 or abs(0.5 - remainder) < half_epsilon  # noqa: RUF069  exact fast path + epsilon fallback, as above
        if is_half:
            result = math.copysign(integral, normalized_value)
        else:
            result = _round_half_away_from_zero(
                normalized_value - math.copysign(half_epsilon, normalized_value)
            )
    elif rounding_method == "UP":
        result = math.trunc(
            normalized_value + math.copysign(1 - trunc_epsilon, normalized_value)
        )
    elif rounding_method == "DOWN":
        result = math.trunc(
            normalized_value + math.copysign(trunc_epsilon, normalized_value)
        )
    else:
        msg = f"unknown rounding method: {rounding_method}"
        raise ValueError(msg)

    if not inverted:
        rounded = float(result * rounding_factor)
    elif rounding_factor.is_integer():
        rounded = result / rounding_factor
    else:
        # 1/0.03 is not a float, so dividing by it lands an ulp off the multiple
        rounded = float(Decimal(result) * Decimal(repr(step)))
    return rounded or 0.0


def _is_zero_r(value: float, epsilon: float) -> bool:
    return (
        value == 0.0  # noqa: RUF069  exact-zero fast path; the epsilon test after `or` is the real check
        or abs(_round_r(value, epsilon)) < epsilon
    )


def float_is_zero(
    value: float,
    precision_digits: int | None = None,
    precision_rounding: float | None = None,
) -> bool:
    return _is_zero_r(
        value, _float_check_precision(precision_digits, precision_rounding)
    )


def float_compare(
    value1: float,
    value2: float,
    precision_digits: int | None = None,
    precision_rounding: float | None = None,
) -> Literal[-1, 0, 1]:
    rounding_factor = _float_check_precision(precision_digits, precision_rounding)
    if value1 == value2:
        return 0
    delta = _round_r(value1, rounding_factor) - _round_r(value2, rounding_factor)
    if _is_zero_r(delta, rounding_factor):
        return 0
    return -1 if delta < 0.0 else 1


def float_repr(value: float, precision_digits: int) -> str:
    if _is_zero_r(value, _float_check_precision(precision_digits=precision_digits)):
        value = 0.0
    return f"{value:.{precision_digits}f}"


def float_split_str(value: float, precision_digits: int) -> tuple[str, str]:
    value = float_round(value, precision_digits=precision_digits)
    value_repr = float_repr(value, precision_digits)
    if precision_digits:
        parts = value_repr.split(".")
        return (parts[0], parts[1])
    return (value_repr, "")


def float_split(value: float, precision_digits: int) -> tuple[int, int]:
    units, cents = float_split_str(value, precision_digits)
    if not cents:
        return int(units), 0
    return int(units), int(cents)


def json_float_round(
    value: float,
    precision_digits: int,
    rounding_method: RoundingMethod = "HALF-UP",
) -> float:
    rounded_value = float_round(
        value,
        precision_digits=precision_digits,
        rounding_method=rounding_method,
    )
    rounded_repr = float_repr(rounded_value, precision_digits=precision_digits)
    return float(rounded_repr)


_INVERTDICT = {
    1e-1: 1e1,
    1e-2: 1e2,
    1e-3: 1e3,
    1e-4: 1e4,
    1e-5: 1e5,
    1e-6: 1e6,
    1e-7: 1e7,
    1e-8: 1e8,
    1e-9: 1e9,
    1e-10: 1e10,
    2e-1: 5e0,
    2e-2: 5e1,
    2e-3: 5e2,
    2e-4: 5e3,
    2e-5: 5e4,
    2e-6: 5e5,
    2e-7: 5e6,
    2e-8: 5e7,
    2e-9: 5e8,
    2e-10: 5e9,
    5e-1: 2e0,
    5e-2: 2e1,
    5e-3: 2e2,
    5e-4: 2e3,
    5e-5: 2e4,
    5e-6: 2e5,
    5e-7: 2e6,
    5e-8: 2e7,
    5e-9: 2e8,
    5e-10: 2e9,
}


def float_invert(value: float) -> float:
    if not value:
        raise ZeroDivisionError("cannot invert 0")
    result = _INVERTDICT.get(value)
    if result is None:
        result = float(1 / Decimal(repr(value)))
    return result
