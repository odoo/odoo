# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import io
import re

from datetime import datetime
from hashlib import md5
from logging import getLogger
from PyPDF2 import PdfFileWriter, PdfFileReader
from PyPDF2.generic import DictionaryObject, NameObject, ArrayObject, DecodedStreamObject, NumberObject, createStringObject, ByteStringObject
from zlib import compress, decompress

try:
    from fontTools.ttLib import TTFont
except ImportError:
    TTFont = None

from odoo.tools.misc import file_open

_logger = getLogger(__name__)
DEFAULT_PDF_DATETIME_FORMAT = "D:%Y%m%d%H%M%S+00'00'"
REGEX_SUBTYPE_UNFORMATED = re.compile(r'^\w+/[\w-]+$')
REGEX_SUBTYPE_FORMATED = re.compile(r'^/\w+#2F[\w-]+$')


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

        try:
            file_path = self.trailer["/Root"].get("/Names", {}).get("/EmbeddedFiles", {}).get("/Names")

            if not file_path:
                return []
            for i in range(0, len(file_path), 2):
                attachment = file_path[i+1].getObject()
                yield (attachment["/F"], attachment["/EF"]["/F"].getObject().getData())
        except Exception:
            # malformed pdf (i.e. invalid xref page)
            return []


class OdooPdfFileWriter(PdfFileWriter):

    def __init__(self, *args, **kwargs):
        """
        Override of the init to initialise additional variables.
        :param pdf_content: if given, will initialise the reader with the pdf content.
        """
        super().__init__(*args, **kwargs)
        self._reader = None
        self.is_pdfa = False

    def addAttachment(self, name, data, subtype=None):
        """
        Add an attachment to the pdf. Supports adding multiple attachment, while respecting PDF/A rules.
        :param name: The name of the attachement
        :param data: The data of the attachement
        :param subtype: The mime-type of the attachement. This is required by PDF/A, but not essential otherwise.
        It should take the form of "/xxx#2Fxxx". E.g. for "text/xml": "/text#2Fxml"
        """
        adapted_subtype = subtype
        if subtype:
            # If we receive the subtype in an 'unformated' (mimetype) format, we'll try to convert it to a pdf-valid one
            if REGEX_SUBTYPE_UNFORMATED.match(subtype):
                adapted_subtype = '/' + subtype.replace('/', '#2F')

            if not REGEX_SUBTYPE_FORMATED.match(adapted_subtype):
                # The subtype still does not match the correct format, so we will not add it to the document
                _logger.warning("Attempt to add an attachment with the incorrect subtype '%s'. The subtype will be ignored.", subtype)
                adapted_subtype = ''

        attachment = self._create_attachment_object({
            'filename': name,
            'content': data,
            'subtype': adapted_subtype,
        })
        if self._root_object.get('/Names') and self._root_object['/Names'].get('/EmbeddedFiles'):
            names_array = self._root_object["/Names"]["/EmbeddedFiles"]["/Names"]
            names_array.extend([attachment.getObject()['/F'], attachment])
        else:
            names_array = ArrayObject()
            names_array.extend([attachment.getObject()['/F'], attachment])

            embedded_files_names_dictionary = DictionaryObject()
            embedded_files_names_dictionary.update({
                NameObject("/Names"): names_array
            })
            embedded_files_dictionary = DictionaryObject()
            embedded_files_dictionary.update({
                NameObject("/EmbeddedFiles"): embedded_files_names_dictionary
            })
            self._root_object.update({
                NameObject("/Names"): embedded_files_dictionary
            })

        if self._root_object.get('/AF'):
            attachment_array = self._root_object['/AF']
            attachment_array.extend([attachment])
        else:
            # Create a new object containing an array referencing embedded file
            # And reference this array in the root catalogue
            attachment_array = self._addObject(ArrayObject([attachment]))
            self._root_object.update({
                NameObject("/AF"): attachment_array
            })

    def embed_odoo_attachment(self, attachment, subtype=None):
        assert attachment, "embed_odoo_attachment cannot be called without attachment."
        self.addAttachment(attachment.name, attachment.raw, subtype=subtype or attachment.mimetype)

    def cloneReaderDocumentRoot(self, reader):
        super().cloneReaderDocumentRoot(reader)
        self._reader = reader
        # Try to read the header coming in, and reuse it in our new PDF
        # This is done in order to allows modifying PDF/A files after creating them (as PyPDF does not read it)
        stream = reader.stream
        stream.seek(0)
        header = stream.readlines(9)
        # Should always be true, the first line of a pdf should have 9 bytes (%PDF-1.x plus a newline)
        if len(header) == 1:
            # If we found a header, set it back to the new pdf
            self._header = header[0]
            # Also check the second line. If it is PDF/A, it should be a line starting by % following by four bytes + \n
            second_line = stream.readlines(1)[0]
            if second_line.decode('latin-1')[0] == '%' and len(second_line) == 6:
                self._header += second_line
                self.is_pdfa = True
        # Look if we have an ID in the incoming stream and use it.
        pdf_id = reader.trailer.get('/ID', None)
        if pdf_id:
            self._ID = pdf_id

    def convert_to_pdfa(self):
        """
        Transform the opened PDF file into a PDF/A compliant file
        """
        # Set the PDF version to 1.7 (as PDF/A-3 is based on version 1.7) and make it PDF/A compliant.
        # See https://github.com/veraPDF/veraPDF-validation-profiles/wiki/PDFA-Parts-2-and-3-rules#rule-612-1

        # " The file header shall begin at byte zero and shall consist of "%PDF-1.n" followed by a single EOL marker,
        # where 'n' is a single digit number between 0 (30h) and 7 (37h) "
        # " The aforementioned EOL marker shall be immediately followed by a % (25h) character followed by at least four
        # bytes, each of whose encoded byte values shall have a decimal value greater than 127 "
        self._header = b"%PDF-1.7\n%\xFF\xFF\xFF\xFF"

        # Add a document ID to the trailer. This is only needed when using encryption with regular PDF, but is required
        # when using PDF/A
        pdf_id = ByteStringObject(md5(self._reader.stream.getvalue()).digest())
        # The first string is based on the content at the time of creating the file, while the second is based on the
        # content of the file when it was last updated. When creating a PDF, both are set to the same value.
        self._ID = ArrayObject((pdf_id, pdf_id))

        with file_open('data/files/sRGB2014.icc', subdir='tools', mode='rb') as icc_profile:
            icc_profile_file_data = compress(icc_profile.read())

        icc_profile_stream_obj = DecodedStreamObject()
        icc_profile_stream_obj.setData(icc_profile_file_data)
        icc_profile_stream_obj.update({
            NameObject("/Filter"): NameObject("/FlateDecode"),
            NameObject("/N"): NumberObject(3),
            NameObject("/Length"): NameObject(str(len(icc_profile_file_data))),
        })

        icc_profile_obj = self._addObject(icc_profile_stream_obj)

        output_intent_dict_obj = DictionaryObject()
        output_intent_dict_obj.update({
            NameObject("/S"): NameObject("/GTS_PDFA1"),
            NameObject("/OutputConditionIdentifier"): createStringObject("sRGB"),
            NameObject("/DestOutputProfile"): icc_profile_obj,
            NameObject("/Type"): NameObject("/OutputIntent"),
        })

        output_intent_obj = self._addObject(output_intent_dict_obj)
        self._root_object.update({
            NameObject("/OutputIntents"): ArrayObject([output_intent_obj]),
        })

        pages = self._root_object['/Pages']['/Kids']

        # PDF/A needs the glyphs width array embedded in the pdf to be consistent with the ones from the font file.
        # But it seems like it is not the case when exporting from wkhtmltopdf.
        if TTFont:
            fonts = {}
            # First browse through all the pages of the pdf file, to get a reference to all the fonts used in the PDF.
            for page in pages:
                for font in page.getObject()['/Resources']['/Font'].values():
                    for descendant in font.getObject()['/DescendantFonts']:
                        fonts[descendant.idnum] = descendant.getObject()

            # Then for each font, rewrite the width array with the information taken directly from the font file.
            # The new width are calculated such as width = round(1000 * font_glyph_width / font_units_per_em)
            # See: http://martin.hoppenheit.info/blog/2018/pdfa-validation-and-inconsistent-glyph-width-information/
            for font in fonts.values():
                font_file = font['/FontDescriptor']['/FontFile2']
                stream = io.BytesIO(decompress(font_file._data))
                ttfont = TTFont(stream)
                font_upm = ttfont['head'].unitsPerEm
                glyphs = ttfont.getGlyphSet()._hmtx.metrics
                glyph_widths = []
                for key, values in glyphs.items():
                    if key[:5] == 'glyph':
                        glyph_widths.append(NumberObject(round(1000.0 * values[0] / font_upm)))

                font[NameObject('/W')] = ArrayObject([NumberObject(1), ArrayObject(glyph_widths)])
                stream.close()
        else:
            _logger.warning('The fonttools package is not installed. Generated PDF may not be PDF/A compliant.')

        outlines = self._root_object['/Outlines'].getObject()
        outlines[NameObject('/Count')] = NumberObject(1)

        # Set odoo as producer
        self.addMetadata({
            '/Creator': "Odoo",
            '/Producer': "Odoo",
        })
        self.is_pdfa = True

    def add_file_metadata(self, metadata_content):
        """
        Set the XMP metadata of the pdf, wrapping it with the necessary XMP header/footer.
        These are required for a PDF/A file to be completely compliant. Ommiting them would result in validation errors.
        :param metadata_content: bytes of the metadata to add to the pdf.
        """
        # See https://wwwimages2.adobe.com/content/dam/acom/en/devnet/xmp/pdfs/XMP%20SDK%20Release%20cc-2016-08/XMPSpecificationPart1.pdf
        # Page 10/11
        header = b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        footer = b'<?xpacket end="w"?>'
        metadata = b'%s%s%s' % (header, metadata_content, footer)
        file_entry = DecodedStreamObject()
        file_entry.setData(metadata)
        file_entry.update({
            NameObject("/Type"): NameObject("/Metadata"),
            NameObject("/Subtype"): NameObject("/XML"),
            NameObject("/Length"): NameObject(str(len(metadata))),
        })

        # Add the new metadata to the pdf, then redirect the reference to refer to this new object.
        metadata_object = self._addObject(file_entry)
        self._root_object.update({NameObject("/Metadata"): metadata_object})

    def _create_attachment_object(self, attachment):
        ''' Create a PyPdf2.generic object representing an embedded file.

        :param attachment: A dictionary containing:
            * filename: The name of the file to embed (required)
            * content:  The bytes of the file to embed (required)
            * subtype: The mime-type of the file to embed (optional)
        :return:
        '''
        file_entry = DecodedStreamObject()
        file_entry.setData(attachment['content'])
        file_entry.update({
            NameObject("/Type"): NameObject("/EmbeddedFile"),
            NameObject("/Params"):
                DictionaryObject({
                    NameObject('/CheckSum'): createStringObject(md5(attachment['content']).hexdigest()),
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
