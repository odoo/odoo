from typing import Any

from pypdf import PdfReader, errors, filters, generic
from pypdf import PdfWriter as _Writer
from pypdf.generic import create_string_object

__all__ = [
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


class PdfWriter(_Writer):
    """PdfWriter with fix for None _info attribute."""

    def add_metadata(self, infos: dict[str, Any]) -> None:
        if hasattr(self, "_info") and self._info is None:
            self._info = generic.DictionaryObject()
        super().add_metadata(infos)
