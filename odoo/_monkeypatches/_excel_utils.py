"""
Shared utilities for Excel-related monkeypatches.

This module provides common functionality used by xlsxwriter.py
to sanitize Excel sheet names according to Microsoft Excel restrictions.
"""

import re

# Excel sheet name restrictions:
# - Cannot contain: [ ] : * ? / \
# - Maximum length: 31 characters
# See: https://support.microsoft.com/en-us/office/rename-a-worksheet-3f1f7148-ee83-404d-8ef0-9ff99fbad1f9

_INVALID_EXCEL_CHARS_RE = re.compile(r"[\[\]:*?/\\]")
_MAX_SHEET_NAME_LENGTH = 31


def sanitize_excel_sheet_name(name: str) -> str:
    """Sanitize a string to be used as an Excel sheet name.

    Removes invalid characters and truncates to the maximum allowed length.

    :param name: The proposed sheet name
    :return: A sanitized sheet name safe for Excel
    """
    if not name:
        return name
    # Remove invalid Excel characters: [ ] : * ? / \
    name = _INVALID_EXCEL_CHARS_RE.sub("", name)
    # Truncate to maximum allowed length
    return name[:_MAX_SHEET_NAME_LENGTH]
