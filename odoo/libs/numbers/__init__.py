"""Odoo-agnostic numeric utilities.

Pure Python numeric helpers with no Odoo dependencies.
"""

from .float_utils import (
    float_compare,
    float_is_zero,
    float_repr,
    float_round,
    float_split,
    float_split_str,
)

__all__ = [
    "float_compare",
    "float_is_zero",
    "float_repr",
    "float_round",
    "float_split",
    "float_split_str",
]
