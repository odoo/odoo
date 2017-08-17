# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import closing
from io import BytesIO
from PyPDF2 import PdfFileWriter, PdfFileReader


def merge_pdf(pdf_data):
    ''' Merge a collection of PDF documents in one
    :param list pdf_data: a list of PDF datastrings
    :return: a unique merged PDF datastring
    '''
    writer = PdfFileWriter()
    for document in pdf_data:
        reader = PdfFileReader(BytesIO(document), strict=False)
        for page in range(0, reader.getNumPages()):
            writer.addPage(reader.getPage(page))
    with contextlib.closing(BytesIO()) as _buffer:
        writer.write(_buffer)
        return  _buffer.getvalue()
