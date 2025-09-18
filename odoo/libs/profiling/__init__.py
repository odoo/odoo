"""Profiling and performance analysis utilities.

Pure Python profiling tools with no Odoo dependencies.
"""

from .speedscope import Speedscope
from .sourcemap_generator import SourceMapGenerator

__all__ = [
    "SourceMapGenerator",
    "Speedscope",
]
