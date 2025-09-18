"""JSON utilities.

Pure Python JSON helpers with no Odoo dependencies.
"""

from .fast_clone import fast_clone
from .orjson_wrapper import (
    OPT_SORT_KEYS,
    ORJSON_AVAILABLE,
    dumps,
    dumps_bytes,
    loads,
)
from .scriptsafe import (
    JSON_SCRIPTSAFE_MAPPER,
    ScriptSafe,
    ScriptSafeJSON,
    scriptsafe,
)

__all__ = [
    "JSON_SCRIPTSAFE_MAPPER",
    "OPT_SORT_KEYS",
    "ORJSON_AVAILABLE",
    "ScriptSafe",
    "ScriptSafeJSON",
    "dumps",
    "dumps_bytes",
    "fast_clone",
    "loads",
    "scriptsafe",
]
