from typing import Dict, Any

from pypdf import errors, filters, generic, PageObject, PdfReader as _Reader, PdfWriter as _Writer
from pypdf.annotations import Link
from pypdf.generic import create_string_object, Fit
from pypdf import __version__  # noqa: F401

__all__ = [
    "PageObject",
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


# setters, so that the aliases below stay assignable like the attributes they shadow
def _set_media_box(self, value):
    self.mediabox = value


def _set_crop_box(self, value):
    self.cropbox = value


def _get_fit(fit, *args):
    return {
        '/Fit': Fit.fit,
        '/XYZ': Fit.xyz,
    }[fit](*args)


PageObject.mergePage = lambda self, page2: self.merge_page(page2)
PageObject.compressContentStreams = lambda self: self.compress_content_streams()
PageObject.rotateClockwise = lambda self, angle: self.rotate(angle)
PageObject.mediaBox = property(lambda self: self.mediabox, _set_media_box)
PageObject.cropBox = property(lambda self: self.cropbox, _set_crop_box)
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

    def getFormTextFields(self):
        return self.get_form_text_fields()


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

    def appendPagesFromReader(self, reader, after_page_append=None):
        return self.append_pages_from_reader(reader, after_page_append)

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
