"""Odoo-agnostic text processing utilities.

Pure Python text helpers with no Odoo dependencies.
"""

from .strings import remove_accents, human_size, str2bool, mod10r, get_flag
from .address import street_split, ADDRESS_REGEX
from .html import (
    html_sanitize,
    html_normalize,
    html2plaintext,
    plaintext2html,
    is_html_empty,
    html_keep_url,
    html_to_inner_content,
    append_content_to_html,
    prepend_html_content,
    create_link,
    validate_url,
    tag_quote,
    fromstring,
    safe_attrs,
    SANITIZE_TAGS,
    VOID_ELEMENTS,
    html_escape,
    nl2br,
    nl2br_enclose,
)

__all__ = [
    "ADDRESS_REGEX",
    "SANITIZE_TAGS",
    "VOID_ELEMENTS",
    "append_content_to_html",
    "create_link",
    "fromstring",
    "get_flag",
    "html2plaintext",
    "html_escape",
    "html_keep_url",
    "html_normalize",
    # HTML utilities
    "html_sanitize",
    "html_to_inner_content",
    "human_size",
    "is_html_empty",
    "mod10r",
    "nl2br",
    "nl2br_enclose",
    "plaintext2html",
    "prepend_html_content",
    "remove_accents",
    "safe_attrs",
    "str2bool",
    "street_split",
    "tag_quote",
    "validate_url",
]
