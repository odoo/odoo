from typing import Dict, Any

import pypdf
from pypdf import errors, filters, generic, PdfReader as _Reader, PdfWriter as _Writer
from pypdf.generic import create_string_object

__all__ = [
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


pypdf.PageObject.mergePage = lambda self, page2: self.merge_page(page2)
pypdf.PageObject.mediaBox = property(lambda self: self.mediabox)
# use lambdas (rather than copying) to allow overrides of the base method
generic.PdfObject.getObject = lambda self: self.get_object()
generic.StreamObject.getData = lambda self: self.get_data()
generic.StreamObject.setData = lambda self, data: self.set_data(data)
generic.RectangleObject.getWidth = lambda self: self.width
generic.RectangleObject.getHeight = lambda self: self.height


class PdfReader(_Reader):
    @property
    def isEncrypted(self):
        return self.is_encrypted

    def getPage(self, pageNumber):
        return self.pages[pageNumber]

    def getNumPages(self):
        return len(self.pages)

    @property
    def numPages(self):
        return len(self.pages)

    def getDocumentInfo(self):
        return self.metadata


class PdfWriter(_Writer):
    def add_metadata(self, infos: Dict[str, Any]) -> None:
        if hasattr(self, '_info') and self._info is None:
            self._info = generic.DictionaryObject()
        super().add_metadata(infos)

    def getPage(self, pageNumber):
        return self.pages[pageNumber]

    def getNumPages(self):
        return len(self.pages)

    def addPage(self, page):
        return self.add_page(page)

    def appendPagesFromReader(self, reader):
        return self.append_pages_from_reader(reader)

    def addBlankPage(self, width=None, height=None):
        return self.add_blank_page(width=width, height=height)

    def addAttachment(self, fname, data):
        return self.add_attachment(fname, data)

    def addMetadata(self, infos):
        return self.add_metadata(infos)

    def cloneReaderDocumentRoot(self, reader):
        return self.clone_reader_document_root(reader)

    def getFields(self, *args, **kwargs):
        return self.get_fields(*args, **kwargs)

    def _addObject(self, *args, **kwargs):
        return self._add_object(*args, **kwargs)
