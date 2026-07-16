from PyPDF2 import errors, filters, generic, PdfReader, PdfWriter as _Writer
from PyPDF2.generic import create_string_object
from PyPDF2 import __version__  # noqa: F401

__all__ = [
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


class PdfWriter(_Writer):
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
