"""Odoo-agnostic filesystem utilities.

Pure Python filesystem helpers with no Odoo dependencies.
"""

from . import appdirs
from . import osutil
from . import mimetypes
from .which import which

__all__ = [
    "appdirs",
    "mimetypes",
    "osutil",
    "which",
]
