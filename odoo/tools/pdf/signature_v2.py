import base64
import datetime
import hashlib
import io
from typing import Optional
from asn1crypto import cms, algos, core, x509
import logging

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
    from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.x509 import Certificate, load_pem_x509_certificate
except ImportError:
    # cryptography 41.0.7 and above is supported
    hashes = None
    PrivateKeyTypes = None
    Encoding = None
    load_pem_private_key = None
    padding = None
    Certificate = None
    load_pem_x509_certificate = None

from odoo import _
from odoo.addons.base.models.res_company import ResCompany
from odoo.addons.base.models.res_users import ResUsers
from odoo.tools.pdf import PdfReader, PdfWriter, ArrayObject, ByteStringObject, DictionaryObject, NameObject, NumberObject, create_string_object, DecodedStreamObject as StreamObject

from odoo.tools.pdf import (
    PdfFileReader,
    PdfFileWriter,
    IndirectObject,
    NullObject,
    ArrayObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    FloatObject,
    ByteStringObject,
    ContentStream,
    TextStringObject,
    DecodedStreamObject as StreamObject,
)

from .incremental_pdf_merge import IncrementalPdfMerge
from typing import cast

_logger = logging.getLogger(__name__)

class PdfSignerV2:

    def __init__(self, pdf_raw: bytes, company: Optional[ResCompany] = None, signing_time=None) -> None:
        self.pdf_raw = pdf_raw
        self.signing_time = signing_time
        self.company = company

    def sign_pdf(self, overlay_items: bytes = None, visible_signature: bool = False, field_name: str = "Odoo Signature", signer: Optional[ResUsers] = None):
        if not self.company or not load_pem_x509_certificate:
            return

        incremented_objects = {}
        pdf_merger = IncrementalPdfMerge(self.pdf_raw)
        if overlay_items:
            overlay_pdf = PdfFileReader(overlay_items)
            # pdf_merger = IncrementalPdfMerge(self.pdf_raw)
            # pdf_merger.merge_pdf(overlay_pdf)
            pdf_reader, incremented_objects = pdf_merger._merge_pdf_pages(overlay_pdf)
        else:
            pdf_reader = PdfFileReader(io.BytesIO(self.pdf_raw), strict=False)

        dummy, sig_field_value = self._setup_form(pdf_reader, visible_signature, field_name,  signer)

        start_id = pdf_reader.trailer["/Size"]
        original_startxref = pdf_merger._find_last_startxref(pdf_merger.get_output_stream_value())

        catalog = cast(DictionaryObject, pdf_reader.trailer["/Root"])
        pdf_merger._sweep_indirect_references(catalog, pdf_reader, incremented_objects, start_id)



        root_entry = pdf_reader.trailer.raw_get("/Root")
        if isinstance(root_entry, IndirectObject):
            # It's an indirect dictionary. It is NOT a direct object
            incremented_objects[root_entry.idnum] = pdf_reader.trailer['/Root']

        # 5. Write all objects to the output stream
        output = pdf_merger.output_stream
        new_xref_entries = pdf_merger._write_objects(output, incremented_objects)

        # 6. Generate Xref table
        xref_start, new_size = pdf_merger._write_xref_table(output, new_xref_entries)

        # 7. Construct the PDF trailer
        pdf_merger._write_trailer(output, pdf_reader, original_startxref, xref_start, new_size)

        # pdf_merger._write_incremented_pdf(pdf_reader, incremented_objects)
        final_output = pdf_merger.get_output_stream_value()

        # if not self._perform_signature(final_output, sig_field_value):
        #     return

        signed_pdf_bytes = self._perform_signature2(final_output)
        return signed_pdf_bytes
        # out_stream = io.BytesIO()
        # self.writer.write_stream(out_stream)
        # return out_stream

    def _load_key_and_certificate(self) -> tuple[Optional[PrivateKeyTypes], Optional[Certificate]]:
        """Loads the private key

        Returns:
            Optional[PrivateKeyTypes]: a private key object, or None if the key couldn't be loaded.
        """
        if "signing_certificate_id" not in self.company._fields \
            or not self.company.signing_certificate_id.pem_certificate:
            return None, None

        certificate = self.company.signing_certificate_id
        cert_bytes = base64.decodebytes(certificate.pem_certificate)
        private_key_bytes = base64.decodebytes(certificate.private_key_id.content)
        return load_pem_private_key(private_key_bytes, None), load_pem_x509_certificate(cert_bytes)

    def _setup_form(self, pdf_reader: PdfFileReader, visible_signature: bool, field_name: str, signer: Optional[ResUsers] = None) -> tuple[DictionaryObject, DictionaryObject] | None:
        """Creates the /AcroForm and populates it with the appropriate field for the signature

        Args:
            visible_signature (bool): boolean value that determines if the signature should be visible on the document
            field_name (str): the name of the signature field
            signer (Optional[ResUsers]): user that will be used in the visuals of the signature field

        Returns:
            tuple[DictionaryObject, DictionaryObject]: a tuple containing the signature field and the signature content
        """
        writer = PdfFileWriter()  # A temporary PdfFileWriter used to wrap new objects
        catalog = cast(DictionaryObject, pdf_reader.trailer["/Root"])
        if "/AcroForm" not in catalog:
            form = DictionaryObject()
            form.update({
                NameObject("/SigFlags"): NumberObject(3)
            })
            form_ref = writer._add_object(form)

            # self.writer._root_object.update({
            #     NameObject("/AcroForm"): form_ref
            # })
            catalog[NameObject("/AcroForm")] = form_ref
            # catalog[NameObject("/AcroForm")] = form_ref
        else:
            form = cast(DictionaryObject, catalog["/AcroForm"].get_object())
            # Ensure SigFlags are correct (3) so signatures are respected
            if "/SigFlags" not in form:
                form[NameObject("/SigFlags")] = NumberObject(3)
            else:
                # Update existing flags to ensure Append Only mode is allowed
                current_flags = form["/SigFlags"]
                form[NameObject("/SigFlags")] = NumberObject(int(current_flags) | 3)

            # form = self.writer._root_object["/AcroForm"].get_object()


            # SigFlags(3) = SignatureExists = true && AppendOnly = true.
            # The document contains signed signature and must be modified in incremental mode (see https://github.com/pdf-association/pdf-issues/issues/457)
            # form.update({
            #     NameObject("/SigFlags"): NumberObject(3)
            # })

        # Assigning the newly created field to a page
        # page = self.writer.pages[0]
        page = pdf_reader.pages[len(pdf_reader.pages) - 1]

        # Setting up the signature field properties
        signature_field = DictionaryObject()

        # Metadata of the signature field
        # /FT = Field Type, here set to /Sig the signature type
        # /T = name of the field
        # /Type = type of object, in this case annotation (/Annot)
        # /Subtype = type of annotation
        # /F = annotation flags, represented as a 32 bit unsigned integer. 132 corresponds to the Print and Locked flags
        #   Print : corresponds to printing the signature when the page is printed
        #   Locked : preventing the annotation properties to be modfied or the annotation to be deletd by the user
        #   (see section 8.4.2 of the Adobe PDF Reference (v1.7) https://ia601001.us.archive.org/1/items/pdf1.7/pdf_reference_1-7.pdf),
        # /P = page reference, reference to the page where the signature field is located
        signature_field.update({
            NameObject("/FT"): NameObject("/Sig"),
            NameObject("/T"): create_string_object(field_name),
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/F"): NumberObject(132),
            NameObject("/P"): page.indirect_reference,
        })


        # Creating the appearance (visible elements of the signature)
        if visible_signature:
            # --- 1. PREPARE CONTENT (Same as yours, but adding Date) ---
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            line1 = f"Digitally signed by {signer.name} <{signer.email}>"
            line2 = f"Date: {date_str}"
            # TODO: Sanitize to prevent PDF crashes if needed

            # --- 2. DYNAMIC DIMENSION CALCULATION (The Upgrade) ---
            font_size = 10
            padding = 5

            # Estimate text width (Helvetica avg char width is ~0.55 * fontSize)
            avg_char_width = font_size * 0.55
            max_char_count = max(len(line1), len(line2))

            # Calculate required Width and Height
            calc_width = (max_char_count * avg_char_width) + (padding * 4)  # Extra padding for safety
            calc_height = (font_size * 2) + (padding * 4)  # Height for 2 lines + padding

            # --- 3. POSITIONING (Top-Right of Page) ---
            origin = page.mediabox.upper_right
            margin = 20  # Distance from edge of paper

            # Dynamic Rect: [x1, y1, x2, y2]
            # x1 = PageRight - Margin - CalculatedWidth
            x1 = float(origin[0]) - margin - calc_width
            y1 = float(origin[1]) - margin - calc_height
            x2 = float(origin[0]) - margin
            y2 = float(origin[1]) - margin

            rect = [x1, y1, x2, y2]

            # --- 4. CREATE STREAM ---
            stream = StreamObject()

            # Set the visible box size (Internal coordinates 0,0 to w,h)
            stream.update({
                NameObject("/BBox"): ArrayObject([
                    FloatObject(0), FloatObject(0),
                    FloatObject(calc_width), FloatObject(calc_height)
                ]),
                NameObject("/Resources"): DictionaryObject({
                    NameObject("/Font"): DictionaryObject({
                        NameObject("/F1"): DictionaryObject({
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica")
                        })
                    })
                }),
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Form")
            })

            # --- 5. DRAWING OPERATIONS ---
            # We calculate the starting text position to ensure it's inside the padding
            # Line spacing (Leading) = Font Size + 2
            leading = font_size + 2

            # Start X: Padding
            # Start Y: Top of box minus Padding minus (approx height of first line)
            txt_x = padding
            txt_y = calc_height - padding - (font_size * 0.8)

            # q = Save State
            # BT = Begin Text
            # /F1 {size} Tf = Set Font
            # {leading} TL = Set Line Spacing
            # {x} {y} Td = Move Cursor
            # (...) Tj = Draw Text
            # T* = New Line
            # ET = End Text
            # Q = Restore State
            pdf_ops = (
                f"q BT "
                f"/F1 {font_size} Tf "
                f"{leading} TL "
                f"{txt_x:.2f} {txt_y:.2f} Td "
                f"({line1}) Tj T* "
                f"({line2}) Tj "
                f"ET Q"
            )

            stream._data = pdf_ops.encode("latin-1")

            # Update Field
            signature_appearance = DictionaryObject()
            signature_appearance.update({
                NameObject("/N"): stream
            })

            signature_field.update({
                NameObject("/Rect"): ArrayObject([FloatObject(x) for x in rect]),
                NameObject("/AP"): signature_appearance,
            })


            # origin = page.mediabox.upper_right # retrieves the top-right coordinates of the page
            # rect_size = (200, 20) # dimensions of the box (width, height)
            # padding = 5
            #
            # # Box that will contain the signature, defined as [x1, y1, x2, y2]
            # # where (x1, y1) is the bottom left coordinates of the box,
            # # and (x2, y2) the top-right coordinates.
            # rect = [
            #     origin[0] - rect_size[0] - padding,
            #     origin[1] - rect_size[1] - padding,
            #     origin[0] - padding,
            #     origin[1] - padding
            # ]

            # Here is defined the StreamObject that contains the information about the visible
            # parts of the signature
            #
            # Dictionary contents:
            # /BBox = coordinates of the 'visible' box, relative to the /Rect definition of the signature field
            # /Resources = resources needed to properly render the signature,
            #   /Font = dictionary containing the information about the font used by the signature
            #       /F1 = font resource, used to define a font that will be usable in the signature
            # stream = StreamObject()
            # stream.update({
            #     NameObject("/BBox"): self._create_number_array_object([0, 0, rect_size[0], rect_size[1]]),
            #     NameObject("/Resources"): DictionaryObject({
            #         NameObject("/Font"): DictionaryObject({
            #             NameObject("/F1"): DictionaryObject({
            #                 NameObject("/Type"): NameObject("/Font"),
            #                 NameObject("/Subtype"): NameObject("/Type1"),
            #                 NameObject("/BaseFont"): NameObject("/Helvetica")
            #             })
            #         })
            #     }),
            #     NameObject("/Type"): NameObject("/XObject"),
            #     NameObject("/Subtype"): NameObject("/Form")
            # })
            #
            # #
            # content = "Digitally signed"
            # content = create_string_object(f'{content} by {signer.name} <{signer.email}>') if signer is not None else create_string_object(content)
            #
            # # Setting the parameters used to display the text object of the signature
            # # More details on this subject can be found in the sections 4.3 and 5.3
            # # of the Adobe PDF Reference (v1.7) https://ia601001.us.archive.org/1/items/pdf1.7/pdf_reference_1-7.pdf
            # #
            # # Parameters:
            # # q = saves the the current graphics state on the graphics state stack
            # # 0.5 0 0 0.5 0 0 cm = modification of the current transformation matrix. Here used to scale down the text size by 0.5 in x and y
            # # BT = begin text object
            # # /F1 = reference to the font resource named F1
            # # 12 Tf = set the font size to 12
            # # 0 TL = defines text leading, the space between lines, here set to 0
            # # 0 10 Td = moves the text to the start of the next line, expressed in text space units. Here (x, y) = (0, 10)
            # # (text_content) Tj = renders a text string
            # # ET = end text object
            # # Q = Restore the graphics state by removing the most recently saved state from the stack and making it the current state
            # stream._data = f"q 0.5 0 0 0.5 0 0 cm BT /F1 12 Tf 0 TL 0 10 Td ({content}) Tj ET Q".encode()
            # signature_appearence = DictionaryObject()
            # signature_appearence.update({
            #     NameObject("/N"): stream
            # })
            # signature_field.update({
            #     NameObject("/AP"): signature_appearence,
            # })
        else:
            # rect = [0,0,0,0]
            signature_field.update({
                NameObject("/Rect"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0), NumberObject(0)])
            })

        # signature_field.update({
        #     NameObject("/Rect"): self._create_number_array_object(rect)
        # })

        # Setting up the actual signature contents with placeholders for /Contents and /ByteRange
        #
        # Dictionary contents:
        # /Contents = content of the signature field. The content is a byte string of an object that follows
        # the Cryptographic Message Syntax (CMS). The object is converted in hexadecimal and stored as bytes.
        # The /Contents are pre-filled with placeholder values of an arbitrary size (i.e. 8KB) to ensure that
        # the signature will fit in the "<>" bounds of the field
        # /ByteRange = an array represented as [offset, length, offset, length, ...] which defines the bytes that
        # are used when computing the digest of the document. Similarly to the /Contents, the /ByteRange is set to
        # a placeholder as we aren't yet able to compute the range at this point.
        # /Type = the type of form field. Here /Sig, the signature field
        # /Filter
        # /SubFilter
        # /M = the timestamp of the signature. Indicates when the document was signed.

        # Production Approach: Reserve 60 bytes for the ByteRange array
        # This allows for 4 large 10-digit offsets + spaces.
        byte_range_placeholder = TextStringObject(" " * 60)

        signature_field_value = DictionaryObject()
        signature_field_value.update({
            NameObject("/Type"): NameObject("/Sig"),
            NameObject("/Contents"): ByteStringObject(b"\0" * 8192),
            NameObject("/ByteRange"): byte_range_placeholder, #self._create_number_array_object([0, 0, 0, 0]),
            NameObject("/Filter"): NameObject("/Adobe.PPKLite"),
            NameObject("/SubFilter"): NameObject("/adbe.pkcs7.detached"),
            NameObject("/M"): create_string_object(datetime.datetime.now(datetime.timezone.utc).strftime("D:%Y%m%d%H%M%S")),
        })

        # Here we add the reference to be written in a specific order. This is needed
        # by Adobe Acrobat to consider the signature valid.
        signature_field_ref = writer._add_object(signature_field)
        signature_field_value_ref = writer._add_object(signature_field_value)

        # /V = the actual value of the signature field. Used to store the dictionary of the field
        signature_field.update({
            NameObject("/V"): signature_field_value_ref
        })

        # Definition of the fields array linked to the form (/AcroForm)
        if "/Fields" not in catalog:
            fields = ArrayObject()
        else:
            fields = catalog["/Fields"].get_object()
        fields.append(signature_field_ref)
        form.update({
            NameObject("/Fields"): fields
        })

        # The signature field reference is added to the annotations array
        if "/Annots" not in page:
            page[NameObject("/Annots")] = ArrayObject()
        page[NameObject("/Annots")].append(signature_field_ref)

        return signature_field, signature_field_value

    def _get_cms_object(self, digest: bytes) -> Optional[cms.ContentInfo]:
        """Creates an object that follows the Cryptographic Message Syntax(CMS)

        RFC: https://datatracker.ietf.org/doc/html/rfc5652

        Args:
            digest (bytes): the digest of the document in bytes

        Returns:
            cms.ContentInfo: a CMS object containing the information of the signature
        """
        private_key, certificate = self._load_key_and_certificate()
        if private_key == None or certificate == None:
            return None
        cert = x509.Certificate.load(
            certificate.public_bytes(encoding=Encoding.DER))
        encap_content_info = {
            'content_type': 'data',
            'content': None
        }

        attrs = cms.CMSAttributes([
            cms.CMSAttribute({
                'type': 'content_type',
                'values': ['data']
            }),
            cms.CMSAttribute({
                'type': 'signing_time',
                'values': [cms.Time({'utc_time': core.UTCTime(self.signing_time or datetime.datetime.now(datetime.timezone.utc))})]
            }),
            cms.CMSAttribute({
                'type': 'cms_algorithm_protection',
                'values': [
                        cms.CMSAlgorithmProtection(
                            {
                                'mac_algorithm': None,
                                'digest_algorithm': cms.DigestAlgorithm(
                                    {'algorithm': 'sha256', 'parameters': None}
                                ),
                                'signature_algorithm': cms.SignedDigestAlgorithm({
                                    'algorithm': 'sha256_rsa',
                                    'parameters': None
                                })
                            }
                        )
                ]
            }),
            cms.CMSAttribute({
                'type': 'message_digest',
                'values': [digest],
            }),
        ])

        signed_attrs = private_key.sign(
            attrs.dump(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        signer_info = cms.SignerInfo({
            'version': "v1",
            'digest_algorithm': algos.DigestAlgorithm({'algorithm': 'sha256'}),
            'signature_algorithm': algos.SignedDigestAlgorithm({'algorithm': 'sha256_rsa'}),
            'signature': signed_attrs,
            'sid': cms.SignerIdentifier({
                'issuer_and_serial_number': cms.IssuerAndSerialNumber({
                    'issuer': cert.issuer,
                    'serial_number': cert.serial_number
                })
            }),
            'signed_attrs': attrs})

        signed_data = {
            'version': 'v1',
            'digest_algorithms': [algos.DigestAlgorithm({'algorithm': 'sha256'})],
            'encap_content_info': encap_content_info,
            'certificates': [cert],
            'signer_infos': [signer_info]
        }

        return cms.ContentInfo({
            'content_type': 'signed_data',
            'content': cms.SignedData(signed_data)
        })

    def _perform_signature2(self, pdf_data: bytes) -> bytes:
        """
        Surgically injects the signature into the LAST signature object found.
        Compatible with documents containing multiple existing signatures.
        """
        pdf_buffer = bytearray(pdf_data)

        # 1. FIND THE TARGET SIGNATURE OBJECT
        # We look for /Type /Sig from the END of the file to hit the latest increment
        sig_obj_start = pdf_buffer.rfind(b"/Type /Sig")
        if sig_obj_start == -1:
            raise ValueError("No signature placeholder found in the incremental update.")

        # 2. LOCATE THE HOLES RELATIVE TO THIS OBJECT
        # We search forward FROM the sig_obj_start to ensure we find the
        # ByteRange and Contents belonging to THIS specific signature object.

        # Locate ByteRange array [ ... ]
        br_key_pos = pdf_buffer.find(b"/ByteRange", sig_obj_start)
        array_start = pdf_buffer.find(b"(", br_key_pos)
        array_end = pdf_buffer.find(b")", array_start) + 1
        placeholder_len = array_end - array_start

        check_byte_range = pdf_buffer[array_start:array_end]

        # Locate Contents hex string < ... >
        c_key_pos = pdf_buffer.find(b"/Contents", sig_obj_start)
        hex_start = pdf_buffer.find(b"<", c_key_pos) + 1  # First byte of hex data
        hex_end = pdf_buffer.find(b">", hex_start)  # Byte after hex data

        check_content_range = pdf_buffer[hex_start-1:hex_end + 1]

        # 3. CALCULATE OFFSETS
        # val1: Start of file
        # val2: Length of first chunk (up to the opening '<')
        # val3: Offset where second chunk starts (after the closing '>')
        # val4: Length of the second chunk (from val3 to EOF)

        val1 = 0
        val2 = hex_start - 1  # The index of the '<'
        val3 = hex_end + 1  # The index after the '>'
        val4 = len(pdf_buffer) - val3

        byte_range = [val1, val2, val3, val4]

        # 4. UPDATE BYTERANGE IN THE BUFFER
        # We format the array and pad with spaces to maintain the exact byte count
        new_range_str = f"[{val1} {val2} {val3} {val4}]".encode('ascii')
        if len(new_range_str) > placeholder_len:
            # This only happens if your dummy values in the first pass were too small
            raise ValueError("ByteRange string exceeds reserved placeholder space.")

        pdf_buffer[array_start:array_end] = new_range_str.ljust(placeholder_len, b" ")

        # 5. HASH THE DOCUMENT
        # We take every byte EXCEPT the hole between hex_start-1 and hex_end+1
        data_to_hash = (
                pdf_buffer[val1: val1 + val2] +
                pdf_buffer[val3: val3 + val4]
        )
        digest = hashlib.sha256(data_to_hash).digest()

        # 6. GENERATE AND INJECT CMS
        cms_content_info = self._get_cms_object(digest)
        signature_hex = cms_content_info.dump().hex().encode('ascii')

        max_hex_len = hex_end - hex_start
        if len(signature_hex) > max_hex_len:
            raise ValueError(f"CMS signature ({len(signature_hex)}) too large for hole ({max_hex_len})")

        # Fill the hole with the signature and pad with '0'
        pdf_buffer[hex_start:hex_end] = signature_hex.ljust(max_hex_len, b"0")

        return bytes(pdf_buffer)

    def _perform_signature(self, pdf_data, sig_field_value: DictionaryObject) -> bool:
        """Creates the actual signature content and populate /ByteRange and /Contents properties with meaningful content.

        Args:
            sig_field_value (DictionaryObject): the value (/V) of the signature field which needs to be modified
        """
        # pdf_data = self._get_document_data()

        # Computation of the location of the last inserted contents for the signature field
        signature_field_pos = pdf_data.rfind(b"/FT /Sig")
        contents_field_pos = pdf_data.find(b"Contents", signature_field_pos)

        # Computing the start and end position of the /Contents <signature> field
        # to exclude the content of <> (aka the actual signature) from the byte range
        placeholder_start = contents_field_pos + 9
        placeholder_end = placeholder_start + len(b"\0" * 8192) * 2 + 2

        # Replacing the placeholder byte range with the actual range
        # that will be used to compute the document digest
        placeholder_byte_range = sig_field_value.get("/ByteRange")

        # Here the byte range represents an array [index, length, index, length, ...]
        # where 'index' represents the index of a byte, and length the number of bytes to take
        # This array indicates the bytes that are used when computing the digest of the document
        byte_range = [0, placeholder_start,
                      placeholder_end, abs(len(pdf_data) - placeholder_end)]

        byte_range = self._correct_byte_range(
            placeholder_byte_range, byte_range, len(pdf_data))

        sig_field_value.update({
            NameObject("/ByteRange"): self._create_number_array_object(byte_range)
        })

        pdf_data = self._get_document_data()

        digest = self._compute_digest_from_byte_range(pdf_data, byte_range)

        cms_content_info = self._get_cms_object(digest)

        if cms_content_info == None:
            return False

        signature_hex = cms_content_info.dump().hex()
        signature_hex = signature_hex.ljust(8192 * 2, "0")

        sig_field_value.update({
            NameObject("/Contents"): ByteStringObject(bytes.fromhex(signature_hex))
        })
        return True

    # def _get_document_data(self):
    #     """Retrieves the bytes of the document from the writer"""
    #     output_stream = io.BytesIO()
    #     self.writer.write_stream(output_stream)
    #     return output_stream.getvalue()


    def _correct_byte_range(self, old_range: list[int], new_range: list[int], base_pdf_len: int) -> list[int]:
        """Corrects the last value of the new byte range

        This function corrects the initial byte range (old_range) which was computed for document containing
        the placeholder values for the /ByteRange and /Contents fields. This is needed because when updating
        /ByteRange, the length of the document will change as the byte range will take more bytes of the
        document, resulting in an invalid byte range.

        Args:
            old_range (list[int]): the previous byte range
            new_range (list[int]): the new byte range
            base_pdf_len (int): the base length of the pdf, before insertion of the actual byte range

        Returns:
            list[int]: the corrected byte range
        """
        # Computing the difference of length of the strings of the old and new byte ranges.
        # Used to determine if a re-computation of the range is needed or not
        current_len = len(str(old_range))
        corrected_len = len(str(new_range))
        diff = corrected_len - current_len

        if diff == 0:
            return new_range

        corrected_range = new_range.copy()
        corrected_range[-1] = abs((base_pdf_len + diff) - new_range[-2])
        return self._correct_byte_range(new_range, corrected_range, base_pdf_len)


    def _compute_digest_from_byte_range(self, data: bytes, byte_range: list[int]) -> bytes:
        """Computes the digest of the data from a byte range. Uses SHA256 algorithm to compute the hash.

        The byte range is defined as an array [offset, length, offset, length, ...] which corresponds to the bytes from the document
        that will be used in the computation of the hash.

        i.e. for document = b'example' and byte_range = [0, 1, 6, 1],
        the hash will be computed from b'ee'

        Args:
            document (bytes): the data in bytes
            byte_range (list[int]): the byte range used to compute the digest.

        Returns:
            bytes: the computed digest
        """
        hashed = hashlib.sha256()
        for i in range(0, len(byte_range), 2):
            hashed.update(data[byte_range[i]:byte_range[i] + byte_range[i+1]])
        return hashed.digest()

    def _create_number_array_object(self, array: list[int]) -> ArrayObject:
        return ArrayObject([NumberObject(item) for item in array])
