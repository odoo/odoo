# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from PyPDF2 import PdfFileWriter, PdfFileReader
from PyPDF2.generic import DictionaryObject, DecodedStreamObject, NameObject, createStringObject, ArrayObject
from PyPDF2.utils import b_
from datetime import datetime

import io
import hashlib


DEFAULT_PDF_DATETIME_FORMAT = "D:%Y%m%d%H%M%S+00'00'"


# make sure values are unwrapped by calling the specialized __getitem__
def _unwrapping_get(self, key, default=None):
    try:
        return self[key]
    except KeyError:
        return default


DictionaryObject.get = _unwrapping_get


class BrandedFileWriter(PdfFileWriter):
    def __init__(self):
        super().__init__()
        self.addMetadata({
            '/Creator': "Odoo",
            '/Producer': "Odoo",
        })


PdfFileWriter = BrandedFileWriter


def merge_pdf(pdf_data):
    ''' Merge a collection of PDF documents in one.
    Note that the attachments are not merged.
    :param list pdf_data: a list of PDF datastrings
    :return: a unique merged PDF datastring
    '''
    writer = PdfFileWriter()
    for document in pdf_data:
        reader = PdfFileReader(io.BytesIO(document), strict=False)
        for page in range(0, reader.getNumPages()):
            writer.addPage(reader.getPage(page))
    with io.BytesIO() as _buffer:
        writer.write(_buffer)
        return _buffer.getvalue()


def rotate_pdf(pdf):
    ''' Rotate clockwise PDF (90°) into a new PDF.
    Note that the attachments are not copied.
    :param pdf: a PDF to rotate
    :return: a PDF rotated
    '''
    writer = PdfFileWriter()
    reader = PdfFileReader(io.BytesIO(pdf), strict=False)
    for page in range(0, reader.getNumPages()):
        page = reader.getPage(page)
        page.rotateClockwise(90)
        writer.addPage(page)
    with io.BytesIO() as _buffer:
        writer.write(_buffer)
        return _buffer.getvalue()

# by default PdfFileReader will overwrite warnings.showwarning which is what
# logging.captureWarnings does, meaning it essentially reverts captureWarnings
# every time it's called which is undesirable
old_init = PdfFileReader.__init__
PdfFileReader.__init__ = lambda self, stream, strict=True, warndest=None, overwriteWarnings=True: \
    old_init(self, stream=stream, strict=strict, warndest=None, overwriteWarnings=False)

class OdooPdfFileReader(PdfFileReader):
    # OVERRIDE of PdfFileReader to add the management of multiple embedded files.

    ''' Returns the files inside the PDF.
    :raises NotImplementedError: if document is encrypted and uses an unsupported encryption method.
    '''
    def getAttachments(self):
        if self.isEncrypted:
            # If the PDF is owner-encrypted, try to unwrap it by giving it an empty user password.
            self.decrypt('')

        if not self.trailer["/Root"].get("/Names", {}).get("/EmbeddedFiles", {}).get("/Names"):
            return []
        for i in range(0, len(self.trailer["/Root"]["/Names"]["/EmbeddedFiles"]["/Names"]), 2):
            attachment = self.trailer["/Root"]["/Names"]["/EmbeddedFiles"]["/Names"][i+1].getObject()
            yield (attachment["/F"], attachment["/EF"]["/F"].getObject().getData())


class OdooPdfFileWriter(PdfFileWriter):
    # OVERRIDE of PdfFileWriter to add the management of multiple embedded files.

    def _create_attachment_object(self, attachment):
        ''' Create a PyPdf2.generic object representing an embedded file.

        :param attachment: A dictionary containing:
            * filename: The name of the file to embed (require).
            * content:  The content of the file encoded in base64 (require).
        :return:
        '''
        file_entry = DecodedStreamObject()
        file_entry.setData(attachment['content'])
        file_entry.update({
            NameObject("/Type"): NameObject("/EmbeddedFile"),
            NameObject("/Params"):
                DictionaryObject({
                    NameObject('/CheckSum'): createStringObject(hashlib.md5(attachment['content']).hexdigest()),
                    NameObject('/ModDate'): createStringObject(datetime.now().strftime(DEFAULT_PDF_DATETIME_FORMAT)),
                    NameObject('/Size'): NameObject(str(len(attachment['content']))),
                }),
        })
        if attachment.get('subtype'):
            file_entry.update({
                NameObject("/Subtype"): NameObject(attachment['subtype']),
            })
        file_entry_object = self._addObject(file_entry)
        filename_object = createStringObject(attachment['filename'])
        filespec_object = DictionaryObject({
            NameObject("/AFRelationship"): NameObject("/Data"),
            NameObject("/Type"): NameObject("/Filespec"),
            NameObject("/F"): filename_object,
            NameObject("/EF"):
                DictionaryObject({
                    NameObject("/F"): file_entry_object,
                    NameObject('/UF'): file_entry_object,
                }),
            NameObject("/UF"): filename_object,
        })
        if attachment.get('description'):
            filespec_object.update({NameObject("/Desc"): createStringObject(attachment['description'])})
        return self._addObject(filespec_object)

    def addAttachment(self, fname, fdata):
        # OVERRIDE of the AddAttachment method to allow appending attachemnts when some already exist
        if self._root_object.get('/Names') and self._root_object['/Names'].get('/EmbeddedFiles'):
            attachments = self._root_object["/Names"]["/EmbeddedFiles"]["/Names"]
            new_attachment = self._create_attachment_object({'filename': fname, 'content': fdata})
            attachments.extend([new_attachment.getObject()['/F'], new_attachment])
        else:
            super().addAttachment(fname, fdata)
