import re


def strip_document(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def _is_homogeneous(value: str) -> bool:
    return bool(value) and len(set(value)) == 1


def _calculate_digit(value: str, weights: list[int]) -> str:
    total = sum(int(digit) * weight for digit, weight in zip(value, weights, strict=True))
    remainder = total % 11
    return "0" if remainder < 2 else str(11 - remainder)


def validate_cnpj(value: str) -> bool:
    digits = strip_document(value)
    if len(digits) != 14 or _is_homogeneous(digits):
        return False
    first = _calculate_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = _calculate_digit(digits[:12] + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digits[-2:] == first + second


def validate_cpf(value: str) -> bool:
    digits = strip_document(value)
    if len(digits) != 11 or _is_homogeneous(digits):
        return False
    first = _calculate_digit(digits[:9], list(range(10, 1, -1)))
    second = _calculate_digit(digits[:9] + first, list(range(11, 1, -1)))
    return digits[-2:] == first + second


def format_cnpj(value: str) -> str:
    digits = strip_document(value)
    if len(digits) != 14:
        return digits
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def format_cpf(value: str) -> str:
    digits = strip_document(value)
    if len(digits) != 11:
        return digits
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

