# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from PyPDF2 import PdfFileWriter, PdfFileReader

import io

from pikepdf import Pdf, AttachedFileSpec


class BrandedFileWriter(PdfFileWriter):
    def __init__(self):
        super().__init__()
        self.addMetadata({
            '/Creator': "Odoo",
            '/Producer': "Odoo",
        })


PdfFileWriter = BrandedFileWriter


class OdooPdf(Pdf):
    def new(*args, **kwargs) -> 'OdooPdf':
        pdf = Pdf.new(*args, **kwargs)
        pdf.__class__ = OdooPdf
        return pdf

    def open(*args, **kwargs) -> 'OdooPdf':
        pdf = Pdf.open(*args, **kwargs)
        pdf.__class__ = OdooPdf
        return pdf

    def save(self, *args, **kwargs):
        with self.open_metadata(set_pikepdf_as_editor=False) as meta:
            meta['xmp:CreatorTool'] = 'Odoo'
            meta['pdf:Producer'] = "Odoo"
        super().save(*args, **kwargs)

    def get_attachments(self):
        for key, value in self.attachments.items():
            yield (key, value.get_file().read_bytes())

    def add_attachment(self, fname, fdata):
        self.attachments[fname] = AttachedFileSpec(self, data=fdata)



def merge_pdf(pdfs_data):
    ''' Merge a collection of PDF documents in one.
    Note that the attachments are not merged.
    :param list pdf_data: a list of PDF datastrings
    :return: a unique merged PDF datastring
    '''
    merged = OdooPdf.new()
    for pdf_data in pdfs_data:
        with OdooPdf.open(io.BytesIO(pdf_data)) as src:
            merged.pages.extend(src.pages)
    with io.BytesIO() as _buffer:
        merged.save(_buffer)
        return _buffer.getvalue()


def rotate_pdf(pdf_data):
    ''' Rotate clockwise PDF (90°) into a new PDF.
    :param pdf: a PDF to rotate
    :return: a PDF rotated
    '''
    with OdooPdf.open(io.BytesIO(pdf_data)) as pdf, io.BytesIO() as _buffer:
        for page in pdf.pages:
            page.rotate(90, relative=True)
        pdf.save(_buffer)
        return _buffer.getvalue()

# by default PdfFileReader will overwrite warnings.showwarning which is what
# logging.captureWarnings does, meaning it essentially reverts captureWarnings
# every time it's called which is undesirable
old_init = PdfFileReader.__init__
PdfFileReader.__init__ = lambda self, stream, strict=True, warndest=None, overwriteWarnings=True: \
    old_init(self, stream=stream, strict=strict, warndest=None, overwriteWarnings=False)
