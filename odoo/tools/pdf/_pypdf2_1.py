from PyPDF2 import filters, generic, utils as errors, PdfFileReader, PdfFileWriter
from PyPDF2.generic import createStringObject as create_string_object
from PyPDF2.pdf import PageObject
from PyPDF2 import __version__  # noqa: F401

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
def _set_crop_box(self, value):
    self.cropBox = value


def _set_lower_left(self, value):
    self.lowerLeft = value


def _set_media_box(self, value):
    self.mediaBox = value


def _set_upper_right(self, value):
    self.upperRight = value


def _set_indirect_reference(self, value):
    self.indirectRef = value


PageObject.add_transformation = lambda self, ctm: self.addTransformation(ctm)
PageObject.cropbox = property(lambda self: self.cropBox, _set_crop_box)
PageObject.mediabox = property(lambda self: self.mediaBox, _set_media_box)
PageObject.indirect_reference = property(lambda self: self.indirectRef, _set_indirect_reference)
generic.PdfObject.get_object = lambda self: self.getObject()
generic.RectangleObject.lower_left = property(lambda self: self.lowerLeft, _set_lower_left)
generic.RectangleObject.upper_right = property(lambda self: self.upperRight, _set_upper_right)


# by default PdfFileReader will overwrite warnings.showwarning which is what
# logging.captureWarnings does, meaning it essentially reverts captureWarnings
# every time it's called which is undesirable
class PdfReader(PdfFileReader):
    def __init__(self, stream, strict=True, warndest=None, overwriteWarnings=True):
        super().__init__(stream, strict=strict, warndest=warndest, overwriteWarnings=False)

    def getFormTextFields(self):
        if self.getFields() is None:
            # Prevent this version of PyPDF2 from trying to iterate over `None`
            return None
        return super().getFormTextFields()


class PdfWriter(PdfFileWriter):
    def get_fields(self, *args, **kwargs):
        return self.getFields(*args, **kwargs)

    def _add_object(self, *args, **kwargs):
        return self._addObject(*args, **kwargs)

    def write_stream(self, stream):
        return self.write(stream)
