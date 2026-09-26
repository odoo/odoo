import warnings

from PyPDF2 import errors, filters, generic, PdfReader, PdfWriter as _Writer
from PyPDF2.generic import AnnotationBuilder, create_string_object
from PyPDF2._page import PageObject
from PyPDF2 import __version__  # noqa: F401

__all__ = [
    "Fit",
    "Link",
    "PageObject",
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


class Fit:
    """Minimal stand-in for pypdf.generic.Fit: PyPDF2 2.x has no such class and
    instead takes the fit type and its zoom args as separate positional arguments."""
    def __init__(self, fit_type, fit_args=()):
        self.fit_type = fit_type
        self.fit_args = fit_args

    @classmethod
    def xyz(cls, left=None, top=None, zoom=None):
        return cls('/XYZ', (left, top, zoom))

    @classmethod
    def fit(cls):
        return cls('/Fit')


def Link(*, rect, border=None, target_page_index=None, fit=None):
    """Minimal stand-in for pypdf.annotations.Link: PyPDF2 2.x has no annotations
    module and instead builds the annotation dict through AnnotationBuilder.link()."""
    fit = fit or Fit.fit()
    return AnnotationBuilder.link(
        rect=rect,
        border=border,
        target_page_index=target_page_index,
        fit=fit.fit_type,
        fit_args=fit.fit_args,
    )


class PdfWriter(_Writer):
    def getFields(self, *args, **kwargs):
        warnings.warn("getFields() is deprecated, use get_fields()", category=DeprecationWarning, stacklevel=2)
        return self.get_fields(*args, **kwargs)

    def _addObject(self, *args, **kwargs):
        warnings.warn("_addObject() is deprecated, use _add_object()", category=DeprecationWarning, stacklevel=2)
        return self._add_object(*args, **kwargs)

    def add_outline_item(self, title, page_number, parent=None, color=None, bold=False, italic=False, fit=None):
        fit = fit or Fit.fit()
        return super().add_outline_item(
            title, page_number, parent, color, bold, italic, fit.fit_type, *fit.fit_args,
        )
