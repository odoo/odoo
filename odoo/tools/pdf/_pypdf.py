import typing

from pypdf import errors, filters, generic, PageObject, PdfReader as _Reader, PdfWriter as _Writer
from pypdf.annotations import Link
from pypdf.generic import create_string_object, Fit
from pypdf import __version__  # noqa: F401

from odoo.tools.func import deprecated

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


deprecate = deprecated("PyPDF2 1.x compatibility shims are deprecated, switch to modern API")


def _get_fit(fit, *args):
    return {
        '/Fit': Fit.fit,
        '/XYZ': Fit.xyz,
    }[fit](*args)


class PdfReader(_Reader):
    @property
    @deprecate
    def isEncrypted(self):
        return self.is_encrypted

    @deprecate
    def getPage(self, pageNumber):
        return self.pages[pageNumber]

    @deprecate
    def getNumPages(self):
        return len(self.pages)

    @property
    @deprecate
    def numPages(self):
        return len(self.pages)

    @deprecate
    def getDocumentInfo(self):
        return self.metadata

    @deprecate
    def getFormTextFields(self):
        return self.get_form_text_fields()


class PdfWriter(_Writer):
    # NOTE: can drop this when pypdf2 shims are removed: issue was fixed in
    # pypdf 5.2 and debian and ubuntu jumped directly to 5.4
    def add_metadata(self, infos: dict[str, typing.Any]) -> None:
        if hasattr(self, '_info') and self._info is None:
            self._info = generic.DictionaryObject()
        super().add_metadata(infos)

    @deprecate
    def getPage(self, pageNumber):
        return self.pages[pageNumber]

    @deprecate
    def getNumPages(self):
        return len(self.pages)

    @deprecate
    def addPage(self, page):
        return self.add_page(page)

    @deprecate
    def appendPagesFromReader(self, reader, after_page_append=None):
        return self.append_pages_from_reader(reader, after_page_append)

    @deprecate
    def addBlankPage(self, width=None, height=None):
        return self.add_blank_page(width=width, height=height)

    @deprecate
    def addAttachment(self, fname, data):
        return self.add_attachment(fname, data)

    @deprecate
    def addMetadata(self, infos):
        return self.add_metadata(infos)

    @deprecate
    def cloneReaderDocumentRoot(self, reader):
        return self.clone_reader_document_root(reader)

    @deprecate
    def getFields(self, *args, **kwargs):
        return self.get_fields(*args, **kwargs)

    @deprecate
    def _addObject(self, *args, **kwargs):
        return self._add_object(*args, **kwargs)

    @deprecate
    def addLink(self, pagenum, pagedest, rect, border=None, fit='/Fit', *args):
        return self.add_annotation(
            page_number=pagenum,
            annotation=Link(
                rect=rect,
                border=border,
                target_page_index=pagedest,
                fit=_get_fit(fit, *args),
            ),
        )

    @deprecate
    def addBookmark(
        self, title, pagenum, parent=None, color=None, bold=False, italic=False, fit='/Fit', *args,
    ):
        return self.add_outline_item(
            title,
            pagenum,
            parent=parent,
            color=color,
            bold=bold,
            italic=italic,
            fit=_get_fit(fit, *args),
        )

    def setPageMode(self, mode):
        self.page_mode = mode
