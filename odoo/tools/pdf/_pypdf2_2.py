from PyPDF2 import errors, filters, generic, PdfReader, PdfWriter as _Writer
from PyPDF2.generic import create_string_object
from PyPDF2 import __version__

from odoo.tools.parse_version import parse_version

# PyPDF2 3.0 turned the legacy camelCase API (numPages, getPage, ...) this shim
# relies on into hard errors: refuse it so the next implementation is tried.
if parse_version(__version__) >= parse_version('3.0'):
    raise ImportError(f"PyPDF2 {__version__} is not supported, use pypdf instead")

__all__ = [
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


class PdfWriter(_Writer):
    def getFields(self, *args, **kwargs):
        return self.get_fields(*args, **kwargs)

    def _addObject(self, *args, **kwargs):
        return self._add_object(*args, **kwargs)
