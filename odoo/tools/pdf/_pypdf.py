import typing

from pypdf import errors, filters, generic, PdfReader as _Reader, PdfWriter as _Writer
from pypdf.generic import create_string_object

from odoo.tools.func import deprecated

__all__ = [
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


deprecate = deprecated("PyPDF2 1.x compatibility shims are deprecated, switch to modern API")


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
    def appendPagesFromReader(self, reader):
        return self.append_pages_from_reader(reader)

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
