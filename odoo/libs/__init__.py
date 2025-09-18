"""Odoo-agnostic libraries and utilities.

This package contains pure Python utilities with NO Odoo dependencies.
These can be used independently of the Odoo framework.

Subpackages:
    - collections: Data structures (OrderedSet, frozendict, Collector, etc.)
    - colors: Color conversion utilities (hex_to_rgb, rgb_to_hex, etc.)
    - datetime: Date/time utilities (date_range, start_of, end_of, etc.)
    - email: Email parsing/formatting (email_normalize, formataddr, etc.)
    - filesystem: File system utilities (appdirs, osutil, mimetypes, etc.)
    - image: Image utilities (image_fix_orientation, image_to_base64, etc.)
    - iteration: Iteration helpers (groupby, unique, topological_sort, etc.)
    - json: JSON utilities (scriptsafe encoding for HTML)
    - locale: Locale conversion utilities (py_to_js_locale, posix_to_ldml)
    - numbers: Numeric utilities (float_round, float_compare, etc.)
    - profiling: Performance profiling tools (speedscope, sourcemap)
    - security: Security utilities
    - soap: SOAP/WSDL client utilities
    - sql: SQL string utilities (escape_psql, make_identifier, etc.)
    - text: Text processing (remove_accents, human_size, street_split, etc.)
    - web: Web utilities (urls)
    - xml: XML utilities (remove_control_characters, create_xml_node, etc.)
    - babel: Babel integration utilities
"""

# Collections
from .collections import (
    OrderedSet,
    LastOrderedSet,
    frozendict,
    freehash,
    Collector,
    StackMap,
    Reverse,
    ReversedIterable,
    ConstantMapping,
    ReadonlyDict,
    DotDict,
    submap,
)

# Iteration
from .iteration import (
    groupby,
    unique,
    partition,
    topological_sort,
    merge_sequences,
    Sentinel,
    SENTINEL,
    reverse_enumerate,
    split_every,
)

# Text
from .text import (
    remove_accents,
    human_size,
    street_split,
    ADDRESS_REGEX,
    str2bool,
    mod10r,
    get_flag,
)

# Utils
from .utils import (
    discardattr,
    is_list_of,
    has_list_types,
    format_frame,
    named_to_positional_printf,
    replace_exceptions,
    _PrintfArgs,
)

__all__ = [
    "ADDRESS_REGEX",
    "SENTINEL",
    "Collector",
    "ConstantMapping",
    "DotDict",
    "LastOrderedSet",
    # Collections
    "OrderedSet",
    "ReadonlyDict",
    "Reverse",
    "ReversedIterable",
    "Sentinel",
    "StackMap",
    "_PrintfArgs",
    # Utils
    "discardattr",
    "format_frame",
    "freehash",
    "frozendict",
    "get_flag",
    # Iteration
    "groupby",
    "has_list_types",
    "human_size",
    "is_list_of",
    "merge_sequences",
    "mod10r",
    "named_to_positional_printf",
    "partition",
    # Text
    "remove_accents",
    "replace_exceptions",
    "reverse_enumerate",
    "split_every",
    "str2bool",
    "street_split",
    "submap",
    "topological_sort",
    "unique",
]
