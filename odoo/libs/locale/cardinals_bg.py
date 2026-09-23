from __future__ import annotations

from decimal import Decimal
from typing import ClassVar, Final

__all__ = [
    "BulgarianNumerals",
]


MASCULINE: Final = 1
FEMININE: Final = -1
NEUTER: Final = 0

UNITS: Final[dict[int, tuple[str, ...]]] = {
    NEUTER: (
        "",
        "едно",
        "две",
        "три",
        "четири",
        "пет",
        "шест",
        "седем",
        "осем",
        "девет",
    ),
    MASCULINE: (
        "",
        "един",
        "два",
        "три",
        "четири",
        "пет",
        "шест",
        "седем",
        "осем",
        "девет",
    ),
    FEMININE: (
        "",
        "една",
        "две",
        "три",
        "четири",
        "пет",
        "шест",
        "седем",
        "осем",
        "девет",
    ),
}

TENS: Final[tuple[str, ...]] = (
    "",
    "десет",
    "двадесет",
    "тридесет",
    "четиридесет",
    "петдесет",
    "шестдесет",
    "седемдесет",
    "осемдесет",
    "деветдесет",
)

HUNDREDS: Final[tuple[str, ...]] = (
    "",
    "сто",
    "двеста",
    "триста",
    "четиристотин",
    "петстотин",
    "шестстотин",
    "седемстотин",
    "осемстотин",
    "деветстотин",
)

ELEVEN: Final = "единадесет"
TEEN_INFIX: Final = "на"

ZERO: Final = "нула"
MINUS: Final = "минус"
AND: Final = "и"
THOUSAND: Final = "хиляда"
THOUSANDS: Final = "хиляди"
SCALE_PLURAL: Final = "а"

SCALES: Final[dict[int, str]] = {
    6: "милион",
    9: "милиард",
    12: "трилион",
    15: "квадрилион",
    18: "квинтилион",
    21: "секстилион",
    24: "септилион",
    27: "октилион",
    30: "ноналион",
    33: "декалион",
    36: "ундекалион",
    39: "дуодекалион",
    42: "тредекалион",
    45: "кватордекалион",
    48: "квинтдекалион",
    51: "сексдекалион",
    54: "септдекалион",
    57: "октодекалион",
    60: "новемдекалион",
    63: "вигинтилион",
}

BEYOND_NAMING: Final = 10 ** (max(SCALES) + 3)


def _spell_teen(unit: int) -> str:
    if unit == 0:
        return TENS[1]
    if unit == 1:
        return ELEVEN
    return UNITS[MASCULINE][unit] + TEEN_INFIX + TENS[1]


def _spell_group(value: int, gender: int, is_final: bool) -> list[str]:
    hundreds, remainder = divmod(value, 100)
    tens, units = divmod(remainder, 10)

    words: list[str] = []
    if hundreds:
        words.append(HUNDREDS[hundreds])
    if tens == 1:
        words.append(_spell_teen(units))
    else:
        if tens:
            words.append(TENS[tens])
        if units:
            words.append(UNITS[gender][units])

    joined_internally = len(words) > 1
    if joined_internally:
        words.insert(len(words) - 1, AND)
    if is_final and (not hundreds or not joined_internally):
        words.insert(0, AND)
    return words


def _spell_scale(power: int, count: int) -> list[str]:
    if power == 3:
        return [THOUSAND] if count == 1 else [THOUSANDS]
    return [SCALES[power] + SCALE_PLURAL] if count > 1 else [SCALES[power]]


def _get_gender_for_power(power: int) -> int:
    if power == 3:
        return FEMININE
    return NEUTER if power == 0 else MASCULINE


def _split_groups(value: int) -> list[int]:
    groups = []
    while value:
        value, group = divmod(value, 1000)
        groups.append(group)
    return list(reversed(groups)) or [0]


class BulgarianNumerals:
    _scales: ClassVar[dict[int, str]] = SCALES

    def str_to_number(self, value: str) -> int | float:
        number = Decimal(value)
        return int(number) if number == number.to_integral_value() else float(number)

    def to_cardinal(self, value: float | None) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            if not value.is_integer():
                msg = "Fractional cardinals are not implemented for Bulgarian"
                raise NotImplementedError(msg)
            value = int(value)
        if abs(value) >= BEYOND_NAMING:
            msg = f"Bulgarian cardinals stop below 10^{max(SCALES) + 3}"
            raise NotImplementedError(msg)
        return self._spell(value)

    def to_ordinal(self, value: int) -> str:
        msg = "Ordinal not implemented for Bulgarian"
        raise NotImplementedError(msg)

    def to_ordinal_num(self, value: int) -> str:
        msg = "Ordinal num not implemented for Bulgarian"
        raise NotImplementedError(msg)

    def to_year(self, value: int) -> str:
        msg = "Year not implemented for Bulgarian"
        raise NotImplementedError(msg)

    def to_currency(self, value: float, **kwargs: object) -> str:
        msg = "Currency not implemented for Bulgarian"
        raise NotImplementedError(msg)

    def _spell(self, value: int) -> str:
        if value == 0:
            return ZERO

        groups = _split_groups(abs(value))
        words: list[str] = [MINUS] if value < 0 else []

        for index, group in enumerate(groups):
            if not group:
                continue
            power = (len(groups) - index - 1) * 3
            is_final = index > 0 and not any(groups[index + 1 :])

            if group == 1 and power >= 3:
                # a lone scale word is a component of its own, and the last
                # component takes "и" as any other would
                if is_final:
                    words.append(AND)
                if power >= 6:
                    words.append(UNITS[MASCULINE][1])
                words.extend(_spell_scale(power, group))
                continue

            words.extend(_spell_group(group, _get_gender_for_power(power), is_final))
            if power:
                words.extend(_spell_scale(power, group))

        return " ".join(words)
