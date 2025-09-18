"""Odoo-agnostic iteration utilities.

Pure Python iteration helpers with no Odoo dependencies.
"""

from .grouping import groupby, unique, partition
from .sorting import topological_sort, merge_sequences
from .sentinel import Sentinel, SENTINEL, PENDING
from .slicing import reverse_enumerate, split_every

__all__ = [
    "PENDING",
    "SENTINEL",
    "Sentinel",
    "groupby",
    "merge_sequences",
    "partition",
    "reverse_enumerate",
    "split_every",
    "topological_sort",
    "unique",
]
