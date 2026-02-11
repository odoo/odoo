import warnings

from PyPDF2 import errors, filters, generic, PdfReader, PdfWriter as _Writer
from PyPDF2.generic import create_string_object

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
        warnings.warn("getFields() is deprecated, use get_fields()", category=DeprecationWarning, stacklevel=2)
        return self.get_fields(*args, **kwargs)

    def _addObject(self, *args, **kwargs):
        warnings.warn("_addObject() is deprecated, use _add_object()", category=DeprecationWarning, stacklevel=2)
        return self._add_object(*args, **kwargs)
