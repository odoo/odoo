from PyPDF2 import filters, generic, utils as errors, PdfFileReader, PdfFileWriter
from PyPDF2.generic import createStringObject as create_string_object

__all__ = [
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


# by default PdfFileReader will overwrite warnings.showwarning which is what
# logging.captureWarnings does, meaning it essentially reverts captureWarnings
# every time it's called which is undesirable
class PdfReader(PdfFileReader):
    def __init__(self, stream, strict=True, warndest=None, overwriteWarnings=True):
        super().__init__(stream, strict=True, warndest=None, overwriteWarnings=False)


class PdfWriter(PdfFileWriter):
    def get_fields(self, *args, **kwargs):
        return self.getFields(*args, **kwargs)

    def _add_object(self, *args, **kwargs):
        return self._addObject(*args, **kwargs)
