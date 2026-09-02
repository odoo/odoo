import typing
<<<<<<< d247bf575787bf76e1d47f2883bdd1300f349559

from pypdf import errors, filters, generic, PdfReader as _Reader, PdfWriter as _Writer
||||||| 0e6a3a06c933efb443dff3c054057509f8269bf8
from pypdf import errors, filters, generic, PdfReader as _Reader, PdfWriter as _Writer
=======
from pypdf import errors, filters, generic, PageObject, PdfReader as _Reader, PdfWriter as _Writer
>>>>>>> 1fa640846d060efdd3d1b197f396319e7366bd5c
from pypdf.generic import create_string_object
from pypdf import __version__  # noqa: F401

from odoo.tools.func import deprecated

__all__ = [
    "PageObject",
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


<<<<<<< d247bf575787bf76e1d47f2883bdd1300f349559
deprecate = deprecated("PyPDF2 1.x compatibility shims are deprecated, switch to modern API")
||||||| 0e6a3a06c933efb443dff3c054057509f8269bf8
# setters, so that the aliases below stay assignable like the attributes they shadow
def _set_media_box(self, value):
    self.mediabox = value


def _set_crop_box(self, value):
    self.cropbox = value


pypdf.PageObject.mergePage = lambda self, page2: self.merge_page(page2)
pypdf.PageObject.compressContentStreams = lambda self: self.compress_content_streams()
pypdf.PageObject.mediaBox = property(lambda self: self.mediabox, _set_media_box)
pypdf.PageObject.cropBox = property(lambda self: self.cropbox, _set_crop_box)
# use lambdas (rather than copying) to allow overrides of the base method
generic.PdfObject.getObject = lambda self: self.get_object()
generic.StreamObject.getData = lambda self: self.get_data()
generic.StreamObject.setData = lambda self, data: self.set_data(data)
generic.RectangleObject.getWidth = lambda self: self.width
generic.RectangleObject.getHeight = lambda self: self.height
=======
# setters, so that the aliases below stay assignable like the attributes they shadow
def _set_media_box(self, value):
    self.mediabox = value


def _set_crop_box(self, value):
    self.cropbox = value


PageObject.mergePage = lambda self, page2: self.merge_page(page2)
PageObject.compressContentStreams = lambda self: self.compress_content_streams()
PageObject.mediaBox = property(lambda self: self.mediabox, _set_media_box)
PageObject.cropBox = property(lambda self: self.cropbox, _set_crop_box)
# use lambdas (rather than copying) to allow overrides of the base method
generic.PdfObject.getObject = lambda self: self.get_object()
generic.StreamObject.getData = lambda self: self.get_data()
generic.StreamObject.setData = lambda self, data: self.set_data(data)
generic.RectangleObject.getWidth = lambda self: self.width
generic.RectangleObject.getHeight = lambda self: self.height
>>>>>>> 1fa640846d060efdd3d1b197f396319e7366bd5c


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
