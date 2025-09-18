"""Email parsing and formatting utilities.

Pure Python email helpers with no Odoo dependencies.
Uses standard library email utilities, idna, and regex.
"""

from .parsing import (
    # Regex patterns
    email_re,
    single_email_re,
    mail_header_msgid_re,
    email_addr_escapes_re,
    address_pattern,
    # Parsing functions
    email_split_tuples,
    email_split,
    email_split_and_format,
    email_split_and_normalize,
    email_split_and_format_normalize,
    extract_rfc2822_addresses,
    # Normalization
    email_normalize,
    email_normalize_all,
    # Formatting
    formataddr,
    encapsulate_email,
    parse_contact_from_email,
    # Domain utilities
    email_domain_extract,
    email_domain_normalize,
    url_domain_extract,
    # Other utilities
    email_anonymize,
    email_escape_char,
    unfold_references,
)

__all__ = [
    "address_pattern",
    "email_addr_escapes_re",
    # Other utilities
    "email_anonymize",
    # Domain utilities
    "email_domain_extract",
    "email_domain_normalize",
    "email_escape_char",
    # Normalization
    "email_normalize",
    "email_normalize_all",
    # Regex patterns
    "email_re",
    "email_split",
    "email_split_and_format",
    "email_split_and_format_normalize",
    "email_split_and_normalize",
    # Parsing functions
    "email_split_tuples",
    "encapsulate_email",
    "extract_rfc2822_addresses",
    # Formatting
    "formataddr",
    "mail_header_msgid_re",
    "parse_contact_from_email",
    "single_email_re",
    "unfold_references",
    "url_domain_extract",
]
