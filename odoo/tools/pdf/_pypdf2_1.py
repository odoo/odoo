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


class PdfReader(PdfFileReader):
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
