import re

from stdnum.exceptions import InvalidFormat

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

MG_NIF_RE = re.compile(r"\d{10}")
MG_STAT_RE = re.compile(r"\d+")
SEPARATORS_RE = re.compile(r"[\s.-]")


def mg_nif_validate(value: str) -> str:
    """Normalize and validate a Malagasy NIF (Numéro d'Identification Fiscale), 10 digits (CPF art. I-01)."""
    value = SEPARATORS_RE.sub("", value)
    if not MG_NIF_RE.fullmatch(value):
        raise InvalidFormat
    return value


def mg_stat_validate(value: str) -> str:
    """Normalize and validate a Malagasy statistical number (numéro d'identification statistique)."""
    value = SEPARATORS_RE.sub("", value)
    if not MG_STAT_RE.fullmatch(value):
        raise InvalidFormat
    return value


MG_ADDITIONAL_IDENTIFIERS_METADATA = {
    "MG_NIF": {
        "sequence": 10,
        "label": _lt("NIF"),
        "help": _lt(
            "Malagasy tax identification number (Numéro d'Identification Fiscale), 10 digits.",
        ),
        "placeholder": "4001234567",
        "display_optional": "show",
        "category": "TIN",
        "validation_function": mg_nif_validate,
        "countries": ["MG"],
    },
    "MG_STAT": {
        "sequence": 20,
        "label": _lt("STAT"),
        "help": _lt(
            "Malagasy statistical identification number, mandatory on invoices (CPF art. IV-21).",
        ),
        "placeholder": "46101112010000123",
        "display_optional": "show",
        "category": "EN",
        "validation_function": mg_stat_validate,
        "countries": ["MG"],
    },
}
