# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
from PyPDF2 import PdfFileWriter, PdfFileReader


def merge_pdf(pdf_data):
    ''' Merge a collection of PDF documents in one
    :param list pdf_data: a list of PDF datastrings
    :return: a unique merged PDF datastring
    '''
    writer = PdfFileWriter()
    for document in pdf_data:
        reader = PdfFileReader(io.BytesIO(document), strict=False)
        for page in range(0, reader.getNumPages()):
            writer.addPage(reader.getPage(page))
    _buffer = io.BytesIO()
    writer.write(_buffer)
    merged_pdf = _buffer.getvalue()
    _buffer.close()
    return merged_pdf


def rotate_pdf(pdf):
    ''' Rotate clockwise PDF (90°)
    :param pdf: a PDF to rotate
    :return: a PDF rotated
    '''
    writer = PdfFileWriter()
    reader = PdfFileReader(io.BytesIO(pdf), strict=False)
    for page in range(0, reader.getNumPages()):
        page = reader.getPage(page)
        page.rotateClockwise(90)
        writer.addPage(page)
    _buffer = io.BytesIO()
    writer.write(_buffer)
    out_pdf = _buffer.getvalue()
    _buffer.close()
    return out_pdf
