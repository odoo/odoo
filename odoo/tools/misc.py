# ruff: noqa: F401
"""
Miscellaneous tools used by Odoo.

This module re-exports utilities from specialized modules for backward compatibility.

.. deprecated:: 19.0
    New code should import from the canonical locations listed below.

CANONICAL IMPORT LOCATIONS
==========================

+----------------------------------+------------------------------------------+
| Function/Class                   | Canonical Import                         |
+==================================+==========================================+
| **File Operations**                                                         |
+----------------------------------+------------------------------------------+
| file_path                        | from odoo.tools.files import ...         |
| file_open                        | from odoo.tools.files import ...         |
| file_open_temporary_directory    | from odoo.tools.files import ...         |
+----------------------------------+------------------------------------------+
| **Locale & Language**                                                       |
+----------------------------------+------------------------------------------+
| get_lang                         | from odoo.tools.locale_utils import ...  |
| get_iso_codes                    | from odoo.tools.locale_utils import ...  |
| scan_languages                   | from odoo.tools.locale_utils import ...  |
| babel_locale_parse               | from odoo.tools.locale_utils import ...  |
| posix_to_ldml, POSIX_TO_LDML     | from odoo.libs.locale import ...         |
+----------------------------------+------------------------------------------+
| **Formatting**                                                              |
+----------------------------------+------------------------------------------+
| formatLang                       | from odoo.tools.formatting import ...    |
| format_date, parse_date          | from odoo.tools.formatting import ...    |
| format_datetime, format_time     | from odoo.tools.formatting import ...    |
| format_amount, format_duration   | from odoo.tools.formatting import ...    |
| format_decimalized_number        | from odoo.tools.formatting import ...    |
| DEFAULT_SERVER_*_FORMAT          | from odoo.tools.formatting import ...    |
+----------------------------------+------------------------------------------+
| **Collections**                                                             |
+----------------------------------+------------------------------------------+
| OrderedSet, LastOrderedSet       | from odoo.libs.collections import ...    |
| frozendict, freehash             | from odoo.libs.collections import ...    |
| Collector, StackMap, Reverse     | from odoo.libs.collections import ...    |
| ConstantMapping, ReadonlyDict    | from odoo.libs.collections import ...    |
| DotDict, submap                  | from odoo.libs.collections import ...    |
+----------------------------------+------------------------------------------+
| **Iteration**                                                               |
+----------------------------------+------------------------------------------+
| groupby, unique, partition       | from odoo.libs.iteration import ...      |
| topological_sort, merge_sequences| from odoo.libs.iteration import ...      |
| reverse_enumerate, split_every   | from odoo.libs.iteration import ...      |
| Sentinel, SENTINEL, PENDING      | from odoo.libs.iteration import ...      |
+----------------------------------+------------------------------------------+
| **Text Processing**                                                         |
+----------------------------------+------------------------------------------+
| remove_accents, human_size       | from odoo.libs.text import ...           |
| street_split, ADDRESS_REGEX      | from odoo.libs.text import ...           |
| str2bool, mod10r, get_flag       | from odoo.libs.text import ...           |
+----------------------------------+------------------------------------------+
| **Security**                                                                |
+----------------------------------+------------------------------------------+
| hmac, hash_sign                  | from odoo.tools.security import ...      |
| verify_hash_signed, consteq      | from odoo.tools.security import ...      |
| limited_field_access_token       | from odoo.tools.security import ...      |
+----------------------------------+------------------------------------------+
| **Subprocess & System**                                                     |
+----------------------------------+------------------------------------------+
| find_in_path, find_pg_tool       | from odoo.tools.subprocess import ...    |
| exec_pg_environ, real_time       | from odoo.tools.subprocess import ...    |
| stripped_sys_argv, dumpstacks    | from odoo.tools.subprocess import ...    |
+----------------------------------+------------------------------------------+
| **Logging**                                                                 |
+----------------------------------+------------------------------------------+
| mute_logger, lower_logging       | from odoo.libs.logging import ...        |
| unquote                          | from odoo.libs.logging import ...        |
+----------------------------------+------------------------------------------+
| **Utilities**                                                               |
+----------------------------------+------------------------------------------+
| discardattr, is_list_of          | from odoo.libs.utils import ...          |
| has_list_types, format_frame     | from odoo.libs.utils import ...          |
| replace_exceptions               | from odoo.libs.utils import ...          |
+----------------------------------+------------------------------------------+

DEFINED IN THIS MODULE (not re-exports)
=======================================
- Callbacks: callback queue for pre/post commit hooks
- clean_context: remove default_* keys from context dict
- get_diff: HTML diff between two texts
- SKIPPED_ELEMENT_TYPES: etree element types to ignore

RE-EXPORTED FROM libs
=====================
- html_escape: from odoo.libs.text.html (canonical: markupsafe.escape)
"""

import collections
import typing
import warnings
from collections.abc import Callable
from difflib import HtmlDiff

from lxml import etree, objectify

# -----------------------------------------------------------------------------
# Collections (Agnostic - no Odoo dependencies)
# Canonical: from odoo.libs.collections import ...
# -----------------------------------------------------------------------------
from odoo.libs.collections import (
    Collector,  # Collect items into groups
    ConstantMapping,  # Mapping returning constant value
    DotDict,  # Dict with attribute access
    LastOrderedSet,  # Set ordered by last access
    OrderedSet,  # Set that preserves insertion order
    ReadonlyDict,  # Read-only dict view
    Reverse,  # Reverse iteration wrapper
    ReversedIterable,  # Reversed iterable type
    StackMap,  # Dict with stack-like shadowing
    freehash,  # Hash for unhashable objects
    frozendict,  # Immutable dictionary
    submap,  # Extract subset of dict keys
)

# -----------------------------------------------------------------------------
# Iteration Utilities (Agnostic - no Odoo dependencies)
# Canonical: from odoo.libs.iteration import ...
# -----------------------------------------------------------------------------
from odoo.libs.iteration import (
    PENDING,  # Stored computed field awaiting recomputation
    SENTINEL,  # Default sentinel instance
    Sentinel,  # Sentinel class for unique markers
    groupby,  # Group items by key (better than itertools.groupby)
    merge_sequences,  # Merge sequences preserving order
    partition,  # Split iterable by predicate
    reverse_enumerate,  # enumerate() in reverse
    split_every,  # Split into chunks of size n
    topological_sort,  # Sort with dependencies
    unique,  # Yield unique items preserving order
)

# -----------------------------------------------------------------------------
# Locale Mapping (Agnostic - no Odoo dependencies)
# Canonical: from odoo.libs.locale import ...
# -----------------------------------------------------------------------------
from odoo.libs.locale import (
    POSIX_TO_LDML,  # Mapping of POSIX to LDML format codes
    posix_to_ldml,  # Convert POSIX format to LDML
)

# -----------------------------------------------------------------------------
# Logging Utilities
# Canonical: from odoo.libs.logging import ...
# -----------------------------------------------------------------------------
from odoo.libs.logging import (
    MungedTracebackLogRecord,  # Log record with munged traceback
    lower_logging,  # Context manager to lower log level
    mute_logger,  # Context manager to suppress logging
    unquote,  # String with unquoted repr()
)

# -----------------------------------------------------------------------------
# Text Processing (Agnostic - no Odoo dependencies)
# Canonical: from odoo.libs.text import ...
# -----------------------------------------------------------------------------
from odoo.libs.text import (
    ADDRESS_REGEX,  # Regex for address parsing
    get_flag,  # Get emoji flag for country code
    human_size,  # Format bytes as "1.2 MB"
    mod10r,  # Modulo 10 recursive check digit
    remove_accents,  # Remove diacritics from string
    str2bool,  # Convert string to boolean
    street_split,  # Split address into components
)

# -----------------------------------------------------------------------------
# General Utilities (Agnostic - no Odoo dependencies)
# Canonical: from odoo.libs.utils import ...
# -----------------------------------------------------------------------------
from odoo.libs.utils import (
    _PrintfArgs,  # Printf argument parser
    discardattr,  # Delete attr if exists (no error)
    format_frame,  # Format stack frame for logging
    has_list_types,  # Check if has list-like types
    is_list_of,  # Check if list of specific type
    named_to_positional_printf,  # Convert named to positional printf
    replace_exceptions,  # Context manager to replace exceptions
)

# -----------------------------------------------------------------------------
# File Operations
# Canonical: from odoo.tools.files import ...
# -----------------------------------------------------------------------------
from .files import (
    file_open,  # Open file from addon
    file_open_temporary_directory,  # Temp dir context manager
    file_path,  # Get absolute path to addon file
)

# -----------------------------------------------------------------------------
# Date/Number Formatting (Odoo-specific, uses environment)
# Canonical: from odoo.tools.formatting import ...
# -----------------------------------------------------------------------------
from .formatting import (
    DATE_LENGTH,
    DATETIME_FORMATS_MAP,
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT,
    # Constants
    NON_BREAKING_SPACE,
    _format_time_ago,  # Format relative time ("2 hours ago")
    format_amount,  # Format amount with currency
    format_date,  # Format date with language settings
    format_datetime,  # Format datetime
    format_decimalized_amount,  # Format monetary amount
    format_decimalized_number,  # Format number with decimals
    format_duration,  # Format duration (hours:minutes)
    format_time,  # Format time
    # Functions
    formatLang,  # Format number with language settings
    parse_date,  # Parse date string
)

# -----------------------------------------------------------------------------
# Locale & Language Utilities
# Canonical: from odoo.tools.locale_utils import ...
# -----------------------------------------------------------------------------
from .locale_utils import (
    babel_locale_parse,  # Parse Babel locale
    get_iso_codes,  # Get ISO language codes
    get_lang,  # Get language record from context
    scan_languages,  # Scan available languages
)

# -----------------------------------------------------------------------------
# Security Utilities
# Canonical: from odoo.tools.security import ...
# -----------------------------------------------------------------------------
from .security import (
    consteq,  # Constant-time string comparison
    hash_sign,  # Hash and sign data
    hmac,  # HMAC signing
    limited_field_access_token,  # Generate field access token
    verify_hash_signed,  # Verify hash signature
    verify_limited_field_access_token,  # Verify field access token
)

# =============================================================================
# RE-EXPORTS FOR BACKWARD COMPATIBILITY
# New code should import from the canonical locations shown in comments
# =============================================================================
# -----------------------------------------------------------------------------
# Subprocess & System Utilities
# Canonical: from odoo.tools.subprocess import ...
# -----------------------------------------------------------------------------
from .subprocess import (
    dumpstacks,  # Dump all thread stacks (debugging)
    exec_pg_environ,  # Get environ dict for pg tools
    find_in_path,  # Find executable in PATH
    find_pg_tool,  # Find PostgreSQL tool (pg_dump, etc.)
    real_time,  # High-precision timestamp
    stripped_sys_argv,  # sys.argv without Odoo-specific args
)

__all__ = [
    "DEFAULT_SERVER_DATETIME_FORMAT",
    "DEFAULT_SERVER_DATE_FORMAT",
    "DEFAULT_SERVER_TIME_FORMAT",
    "NON_BREAKING_SPACE",
    "SKIPPED_ELEMENT_TYPES",
    "DotDict",
    "LastOrderedSet",
    "OrderedSet",
    "Reverse",
    "babel_locale_parse",
    "clean_context",
    "consteq",
    "discardattr",
    "file_open",
    "file_open_temporary_directory",
    "file_path",
    "find_in_path",
    "formatLang",
    "format_amount",
    "format_date",
    "format_datetime",
    "format_duration",
    "format_time",
    "frozendict",
    "get_iso_codes",
    "get_lang",
    "groupby",
    "hash_sign",
    "hmac",
    "html_escape",
    "human_size",
    "is_list_of",
    "merge_sequences",
    "mod10r",
    "mute_logger",
    "parse_date",
    "partition",
    "posix_to_ldml",
    "real_time",
    "remove_accents",
    "replace_exceptions",
    "reverse_enumerate",
    "split_every",
    "str2bool",
    "street_split",
    "topological_sort",
    "unique",
    "verify_hash_signed",
]

# List of etree._Element subclasses that we choose to ignore when parsing XML.
# We include the *Base ones just in case, currently they seem to be subclasses of the _* ones.
SKIPPED_ELEMENT_TYPES = (
    etree._Comment,
    etree._ProcessingInstruction,
    etree.CommentBase,
    etree.PIBase,
    etree._Entity,
)

# Configure default global parser.
# - resolve_entities=False: prevent XXE attacks (since lxml 5.0 default)
# - decompress=False: prevent decompression bomb attacks (lxml 6.0 feature)
etree.set_default_parser(etree.XMLParser(resolve_entities=False, decompress=False))
default_parser = etree.XMLParser(
    resolve_entities=False, remove_blank_text=True, decompress=False
)
default_parser.set_element_class_lookup(objectify.ObjectifyElementClassLookup())
objectify.set_default_parser(default_parser)


def clean_context(context: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """This function take a dictionary and remove each entry with its key
    starting with ``default_``
    """
    return {k: v for k, v in context.items() if not k.startswith("default_")}


class Callbacks:
    """A simple queue of callback functions.  Upon run, every function is
    called (in addition order), and the queue is emptied.

    ::

        callbacks = Callbacks()

        # add foo
        def foo():
            print("foo")

        callbacks.add(foo)

        # add bar
        callbacks.add
        def bar():
            print("bar")

        # add foo again
        callbacks.add(foo)

        # call foo(), bar(), foo(), then clear the callback queue
        callbacks.run()

    The queue also provides a ``data`` dictionary, that may be freely used to
    store anything, but is mostly aimed at aggregating data for callbacks.  The
    dictionary is automatically cleared by ``run()`` once all callback functions
    have been called.

    ::

        # register foo to process aggregated data
        @callbacks.add
        def foo():
            print(sum(callbacks.data['foo']))

        callbacks.data.setdefault('foo', []).append(1)
        ...
        callbacks.data.setdefault('foo', []).append(2)
        ...
        callbacks.data.setdefault('foo', []).append(3)

        # call foo(), which prints 6
        callbacks.run()

    Given the global nature of ``data``, the keys should identify in a unique
    way the data being stored.  It is recommended to use strings with a
    structure like ``"{module}.{feature}"``.
    """

    __slots__ = ["_funcs", "data"]

    def __init__(self):
        self._funcs: collections.deque[Callable] = collections.deque()
        self.data = {}

    def add(self, func: Callable) -> None:
        """Add the given function."""
        self._funcs.append(func)

    def run(self) -> None:
        """Call all the functions (in addition order), then clear associated data."""
        while self._funcs:
            func = self._funcs.popleft()
            func()
        self.clear()

    def clear(self) -> None:
        """Remove all callbacks and data from self."""
        self._funcs.clear()
        self.data.clear()

    def __len__(self) -> int:
        return len(self._funcs)


from odoo.libs.text.html import html_escape  # noqa: E402


def get_diff(data_from, data_to, custom_style=False, dark_color_scheme=False):
    """
    Return, in an HTML table, the diff between two texts.

    :param tuple data_from: tuple(text, name), name will be used as table header
    :param tuple data_to: tuple(text, name), name will be used as table header
    :param tuple custom_style: string, style css including <style> tag.
    :param bool dark_color_scheme: true if dark color scheme is used
    :return: a string containing the diff in an HTML table format.
    """

    def handle_style(html_diff, custom_style, dark_color_scheme):
        """The HtmlDiff lib will add some useful classes on the DOM to
        identify elements. Simply append to those classes some BS4 ones.
        For the table to fit the modal width, some custom style is needed.
        """
        to_append = {
            "diff_header": "bg-600 text-light text-center align-top px-2",
            "diff_next": "d-none",
        }
        for old, new in to_append.items():
            html_diff = html_diff.replace(old, "%s %s" % (old, new))
        html_diff = html_diff.replace("nowrap", "")
        colors = (
            ("#7f2d2f", "#406a2d", "#51232f", "#3f483b")
            if dark_color_scheme
            else ("#ffc1c0", "#abf2bc", "#ffebe9", "#e6ffec")
        )
        html_diff += custom_style or """
            <style>
                .modal-dialog.modal-lg:has(table.diff) {
                    max-width: 1600px;
                    padding-left: 1.75rem;
                    padding-right: 1.75rem;
                }
                table.diff { width: 100%%; }
                table.diff th.diff_header { width: 50%%; }
                table.diff td.diff_header { white-space: nowrap; }
                table.diff td.diff_header + td { width: 50%%; }
                table.diff td { word-break: break-all; vertical-align: top; }
                table.diff .diff_chg, table.diff .diff_sub, table.diff .diff_add {
                    display: inline-block;
                    color: inherit;
                }
                table.diff .diff_sub, table.diff td:nth-child(3) > .diff_chg { background-color: %s }
                table.diff .diff_add, table.diff td:nth-child(6) > .diff_chg { background-color: %s }
                table.diff td:nth-child(3):has(>.diff_chg, .diff_sub) { background-color: %s }
                table.diff td:nth-child(6):has(>.diff_chg, .diff_add) { background-color: %s }
            </style>
        """ % colors
        return html_diff

    diff = HtmlDiff(tabsize=2).make_table(
        data_from[0].splitlines(),
        data_to[0].splitlines(),
        data_from[1],
        data_to[1],
        context=True,  # Show only diff lines, not all the code
        numlines=3,
    )
    return handle_style(diff, custom_style, dark_color_scheme)
