# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import PyPDF2

class BrandedFileWriter(PyPDF2.PdfFileWriter):
    def __init__(self):
        super().__init__()
        self.addMetadata({
            '/Creator': "Odoo",
            '/Producer': "Odoo",
        })
PyPDF2.PdfFileWriter = BrandedFileWriter

def merge_pdf(pdf_data):
    ''' Merge a collection of PDF documents in one
    :param list pdf_data: a list of PDF datastrings
    :return: a unique merged PDF datastring
    '''
    writer = PyPDF2.PdfFileWriter()
    for document in pdf_data:
        reader = PyPDF2.PdfFileReader(io.BytesIO(document), strict=False)
        for page in range(0, reader.getNumPages()):
            writer.addPage(reader.getPage(page))
    with io.BytesIO() as _buffer:
        writer.write(_buffer)
        return _buffer.getvalue()


def rotate_pdf(pdf):
    ''' Rotate clockwise PDF (90°)
    :param pdf: a PDF to rotate
    :return: a PDF rotated
    '''
    writer = PyPDF2.PdfFileWriter()
    reader = PyPDF2.PdfFileReader(io.BytesIO(pdf), strict=False)
    for page in range(0, reader.getNumPages()):
        page = reader.getPage(page)
        page.rotateClockwise(90)
        writer.addPage(page)
    with io.BytesIO() as _buffer:
        writer.write(_buffer)
        return _buffer.getvalue()
