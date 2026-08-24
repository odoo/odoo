from PyPDF2 import filters, generic, utils as errors, PdfFileReader, PdfFileWriter
from PyPDF2.pdf import PageObject
from PyPDF2.generic import createStringObject as create_string_object
from PyPDF2 import __version__  # noqa: F401

__all__ = [
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]

# PyPDF2 1.x only provides the legacy camelCase API, while 2.x and pypdf have
# the modern snake_case one (with camelCase as the deprecated alias). Alias the
# modern names onto 1.x so callers can use the modern API on every backend;
# this whole module can then be dropped once 1.x is no longer supported.
PageObject.mediabox = property(lambda self: self.mediaBox, lambda self, value: setattr(self, "mediaBox", value))
PageObject.cropbox = property(lambda self: self.cropBox, lambda self, value: setattr(self, "cropBox", value))
generic.RectangleObject.width = property(lambda self: self.getWidth())
generic.RectangleObject.height = property(lambda self: self.getHeight())
generic.RectangleObject.lower_left = property(lambda self: self.lowerLeft, lambda self, value: setattr(self, "lowerLeft", value))
generic.RectangleObject.upper_right = property(lambda self: self.upperRight, lambda self, value: setattr(self, "upperRight", value))


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
