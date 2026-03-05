import base64
import datetime
import hashlib
import io
from typing import Optional, cast, Any
from asn1crypto import cms, algos, core, x509
import logging

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
    from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.x509 import Certificate, load_pem_x509_certificates
except ImportError:
    # cryptography 41.0.7 and above is supported
    hashes = None
    PrivateKeyTypes = None
    Encoding = None
    load_pem_private_key = None
    padding = None
    Certificate = None
    load_pem_x509_certificates = None

from odoo import _
from odoo.addons.base.models.res_company import ResCompany
from odoo.addons.base.models.res_users import ResUsers
from odoo.tools.pdf import (
    PdfFileReader,
    PdfFileWriter,
    IndirectObject,
    ArrayObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    FloatObject,
    ByteStringObject,
    DecodedStreamObject as StreamObject,
    create_string_object
)

from .incremental_pdf_merge import IncrementalPdfMerge, b_
from .constants import TrailerKeys as TK, PageAttributes as PG, CatalogDictionary as CD, InteractiveFormDictEntries as IF

_logger = logging.getLogger(__name__)

class PdfSigner:
    """
    Manages the cryptographic signing of PDF documents using incremental updates.

    This class implements the **PAdES** (PDF Advanced Electronic Signatures) standard basics.
    It performs the following operations:

    1.  **Modification:** Modifies the document by adding a signature field via a form
        (AcroForm) and optionally merges a visual overlay.
    2.  **Signing:** Computes a cryptographic signature (PKCS#7/CMS).
    3.  **Injection:** Inserts the signature into the file without invalidating existing
        signatures (incremental update).

    **References:**
    This implementation adheres to the standards defined in:

    * `Adobe PDF Reference (v1.7) <https://ia601001.us.archive.org/1/items/pdf1.7/pdf_reference_1-7.pdf>`_
        (For the general structure of the PDF document).
    * `Digital Signatures in a PDF <https://www.adobe.com/devnet-docs/acrobatetk/tools/DigSig/Acrobat_DigitalSignatures_in_PDF.pdf>`_
        (For the specific structure of the signature dictionary).

    :param pdf_raw: The raw bytes of the original PDF file.
    :type pdf_raw: bytes
    :param company: The Odoo company record containing the signing certificate/key.
    :type company: ResCompany or None
    :param signing_time: Optional datetime to use as the signing timestamp.
                         Defaults to ``datetime.now()``.
    :type signing_time: datetime or None
    """

    def __init__(self, pdf_raw: bytes, company: Optional[ResCompany] = None, signing_time=None) -> None:
        self.pdf_raw = pdf_raw
        self.signing_time = signing_time or datetime.datetime.now(datetime.timezone.utc)
        self.company = company

    def sign_pdf(
            self,
            overlay_items: bytes = None,
            visible_signature: bool = False,
            field_name: str = "Odoo Signature",
            signer: Optional[ResUsers] = None
    ) -> bytes | None:
        """
        Orchestrates the entire signing workflow.

        This method acts as the main entry point. It modifies the PDF structure in-memory
        to add signature fields and visual elements, writes those changes as an
        incremental update, and then physically injects the cryptographic signature
        into the reserved placeholder.

        :param overlay_items: Optional PDF bytes to overlay (e.g., a background or stamp).
        :type overlay_items: bytes or None
        :param visible_signature: If True, generates a visual representation (Widget)
                                  of the signature on the first page.
        :type visible_signature: bool
        :param field_name: The unique internal name for the signature field.
        :type field_name: str
        :param signer: The user record associated with the signature (used for
                       rendering the name in the visible box).
        :type signer: ResUsers or None
        :return: The fully signed PDF bytes, or None if dependencies/keys are missing.
        :rtype: bytes or None
        """
        if not self.company or not load_pem_x509_certificates:
            return

        incremented_objects = {}
        pdf_merger = IncrementalPdfMerge(self.pdf_raw)
        signer_identifier = f"{signer.name} <{signer.email}>"

        # 1. Merge Overlay (if provided) or Load Original
        if overlay_items:
            overlay_pdf = PdfFileReader(overlay_items, strict=False)
            pdf_reader, incremented_objects = pdf_merger._merge_pdf_pages_as_annotation(overlay_pdf, signer_identifier)
        else:
            pdf_reader = PdfFileReader(io.BytesIO(self.pdf_raw), strict=False)

        # 2. Prepare the Signature Field Structure
        self._setup_form(pdf_reader, True, field_name, incremented_objects, signer_identifier)

        # 3. Write the Incremental Update (with empty signature placeholders)
        pdf_merger._write_incremented_pdf(pdf_reader, incremented_objects)
        final_output = pdf_merger.get_output_stream_value()

        # 4. Sign the Document (fill the placeholders)
        signed_pdf_bytes = self._perform_signature(final_output)
        return signed_pdf_bytes

    def _load_key_and_certificate(self) -> tuple[Optional[PrivateKeyTypes], Optional[Certificate], Optional[list[Certificate]]]:
        """
        Retrieves and deserializes the private key and certificate from the company record.

        :return: A tuple ``(private_key, certificate)``. Returns ``(None, None)`` if
                 the company has no valid certificate configured.
        :rtype: tuple
        """
        if "signing_certificate_id" not in self.company._fields \
            or not self.company.signing_certificate_id.pem_certificate:
            return None, None, None

        certificate = self.company.signing_certificate_id
        cert_bytes = base64.decodebytes(certificate.pem_certificate)
        private_key_bytes = base64.decodebytes(certificate.private_key_id.content)
        all_certs = load_pem_x509_certificates(cert_bytes)

        leaf_cert = all_certs[0]
        cert_chain = all_certs[1:]
        private_key = load_pem_private_key(private_key_bytes, None)

        return private_key, leaf_cert, cert_chain

    def _setup_form(
            self,
            pdf_reader: PdfFileReader,
            visible_signature: bool,
            field_name: str,
            incremented_objects: dict[tuple[int, int], Any],
            signed_by: str
    ) -> None:
        """
        Configures the PDF ``/AcroForm`` and creates the Signature Field dictionaries.

        This method modifies the PDF object graph to include:
        1.  **AcroForm Dictionary:** Ensures the document supports forms and sets the
            ``SigFlags`` to 3 (Signatures Exist | Append Only).
        2.  **Signature Field:** A standard PDF Dictionary defining the field attributes
            (``/FT /Sig``, ``/T <name>``, etc.).
        3.  **Visual Appearance (Optional):** If ``visible_signature`` is True, it calculates
            dynamic bounding box dimensions based on the signer's name and generates
            drawing commands (PDF stream) for the signature widget.
        4.  **Signature Value:** A placeholder dictionary containing the empty ``/Contents``
            (hex string) and ``/ByteRange`` array, ready for the cryptographic signature.

        :param pdf_reader: The reader object holding the current PDF state.
        :type pdf_reader: PdfFileReader
        :param visible_signature: Whether to generate visual appearance streams.
        :type visible_signature: bool
        :param field_name: The name of the acro_form field.
        :type field_name: str
        :param signed_by: Text identifier of the user who is signing this document.
        :type signer: str or None
        """
        writer = PdfFileWriter()  # A temporary PdfFileWriter used to wrap new objects
        catalog = cast(DictionaryObject, pdf_reader.trailer[TK.ROOT])

        # --- 1. SETUP ACROFORM ---
        acro_form_originally_exist = False
        if CD.ACRO_FORM not in catalog:
            acro_form = DictionaryObject()
            acro_form.update({
                NameObject(IF.SigFlags): NumberObject(3)
            })
            catalog[NameObject(CD.ACRO_FORM)] = writer._add_object(acro_form)
        else:
            acro_form_originally_exist = True
            acro_form = catalog[CD.ACRO_FORM].get_object()
            # Update flags: Allow Append Mode (Bit 2) | Signatures Exist (Bit 1) = 3
            if IF.SigFlags not in acro_form:
                acro_form[NameObject(IF.SigFlags)] = NumberObject(3)
            else:
                current_flags = acro_form[IF.SigFlags]
                acro_form[NameObject(IF.SigFlags)] = NumberObject(int(current_flags) | 3)

        # --- 2. DEFINE SIGNATURE FIELD METADATA ---
        # We create a Widget Annotation that acts as the signature field.
        # Flags=132 (Print + Locked): Visible when printed, cannot be deleted by user.
        page = pdf_reader.pages[0]
        signature_annotation = DictionaryObject()
        signature_annotation.update({
            NameObject("/FT"): NameObject("/Sig"),  # Field Type: Signature
            NameObject("/T"): create_string_object(field_name),
            NameObject("/Type"): NameObject("/Annot"),  # Object Type: Annotation
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/F"): NumberObject(132),  # Flags: Print | Locked
            NameObject("/P"): page.indirect_reference,
        })

        # --- 3. CONSTRUCT VISUAL APPEARANCE (Optional) ---
        if visible_signature:
            # 1. Text content
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            line1 = f"Digitally signed by {signed_by}"  #TODO: Sanitize to prevent PDF crashes if needed
            line2 = f"Date: {date_str}"

            # 2. Dynamic size calculation (SAFE HEURISTIC)
            font_size = 10
            padding = 5
            avg_char_width = font_size * 0.55

            max_chars = max(len(line1), len(line2))

            calc_width = int((max_chars * avg_char_width) + (padding * 4))
            calc_height = int((font_size * 2) + (padding * 4))

            # 3. Positioning (top-right of page)
            origin = page.mediabox.upper_right
            margin = 20

            x2 = int(origin[0] - margin)
            y2 = int(origin[1] - margin)
            x1 = int(x2 - calc_width)
            y1 = int(y2 - calc_height)

            rect = [x1, y1, x2, y2]

            # 4. Create appearance stream (Form XObject)
            signature_appearance_stream = StreamObject()
            signature_appearance_stream.update({
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Form"),
                NameObject("/BBox"): ArrayObject([
                    NumberObject(0), NumberObject(0),
                    NumberObject(calc_width), NumberObject(calc_height)
                ]),
                NameObject("/Matrix"): ArrayObject([
                    NumberObject(1), NumberObject(0),
                    NumberObject(0), NumberObject(1),
                    NumberObject(0), NumberObject(0)
                ]),
                NameObject("/Resources"): DictionaryObject({
                    NameObject("/Font"): DictionaryObject({
                        NameObject("/F1"): DictionaryObject({
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica")
                        })
                    })
                })
            })

            # 5. Deterministic text layout (NO T*)
            text_y_top = calc_height - padding - font_size
            text_y_bottom = text_y_top - (font_size + 2)

            pdf_ops = (
                "q 1 0 0 1 0 0 cm "
                "BT "
                f"/F1 {font_size} Tf "
                f"{padding} {text_y_top} Td "
                f"({line1}) Tj "
                f"0 {- (font_size + 2)} Td "
                f"({line2}) Tj "
                "ET Q"
            )

            signature_appearance_stream._data = b_(pdf_ops)

            # 6. Attach appearance to signature field
            signature_appearance = DictionaryObject()
            signature_appearance.update({
                NameObject("/N"): signature_appearance_stream
            })

            signature_annotation.update({
                NameObject("/Rect"): ArrayObject([NumberObject(x) for x in rect]),
                NameObject("/AP"): signature_appearance
            })
        else:
            # Invisible signature (Zero-width rect)
            signature_annotation.update({
                NameObject("/Rect"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0), NumberObject(0)])
            })

        # --- 4. PREPARE SIGNATURE VALUE PLACEHOLDERS ---
        # /Contents: A large hex string (0-padded) to hold the CMS signature later.
        # /ByteRange: A placeholder array [0, 0, 0, 0] to hold offsets later.
        # Reserve 60 bytes for ByteRange (enough for four 10-digit integers).
        byte_range_placeholder = ArrayObject([
            NumberObject(0),
            NumberObject(9999999999),
            NumberObject(9999999999),
            NumberObject(9999999999)
        ])

        signature_object = DictionaryObject()
        signature_object.update({
            NameObject("/Type"): NameObject("/Sig"),
            NameObject("/Contents"): ByteStringObject(b"\0" * 8192),
            NameObject("/ByteRange"): byte_range_placeholder,
            NameObject("/Filter"): NameObject("/Adobe.PPKLite"),
            NameObject("/SubFilter"): NameObject("/adbe.pkcs7.detached"),
            NameObject("/M"): create_string_object(self.signing_time.strftime("D:%Y%m%d%H%M%SZ")),
        })

        # Register objects with the temporary writer to get references
        signature_annotation_ref = writer._add_object(signature_annotation)
        signature_object_ref = writer._add_object(signature_object)

        # Link signature value dict to the field dict
        signature_annotation.update({
            NameObject("/V"): signature_object_ref
        })

        # --- 5. REGISTER FIELD IN CATALOG AND PAGE ---
        # Add to /AcroForm /Fields
        try:
            raw_fields = acro_form.raw_get(CD.Fields)
        except KeyError:
            raw_fields = None
        if raw_fields and isinstance(raw_fields, IndirectObject):
            fields_array = raw_fields.get_object()
            fields_array.append(signature_annotation_ref)
            raw_id = raw_fields.idnum
            raw_gen = raw_fields.generation
            if (raw_id, raw_gen) not in incremented_objects:
                incremented_objects[(raw_id, raw_gen)] = fields_array
            pdf_reader.cache_indirect_object(raw_gen, raw_id, fields_array)
        else:
            if raw_fields is None:
                raw_fields = ArrayObject()
            raw_fields.append(signature_annotation_ref)
            acro_form[NameObject(CD.Fields)] = raw_fields

        # Add to Page /Annots
        try:
            raw_annots = page.raw_get(PG.ANNOTS)
        except KeyError:
            raw_annots = None
        if raw_annots and isinstance(raw_annots, IndirectObject):
            annots_array = raw_annots.get_object()
            annots_array.append(signature_annotation_ref)
            raw_id = raw_annots.idnum
            raw_gen = raw_annots.generation
            if (raw_id, raw_gen) not in incremented_objects:
                incremented_objects[(raw_id, raw_gen)] = annots_array
            pdf_reader.cache_indirect_object(raw_gen, raw_id, annots_array)
        else:
            if raw_annots is None:
                raw_annots = ArrayObject()
            raw_annots.append(signature_annotation_ref)
            page[NameObject(PG.ANNOTS)] = raw_annots

            page_ref_id = page.indirect_reference.idnum
            page_ref_gen = page.indirect_reference.generation
            if (page_ref_id, page_ref_gen) not in incremented_objects:
                incremented_objects[(page_ref_id, page_ref_gen)] = page
            pdf_reader.cache_indirect_object(page_ref_gen, page_ref_id, page)


        root_entry = pdf_reader.trailer.raw_get(TK.ROOT)
        if isinstance(root_entry, IndirectObject):
            # If Root is indirect, we must explicitly track it for the incremental update
            incremented_objects[(root_entry.idnum, root_entry.generation)] = catalog
            pdf_reader.cache_indirect_object(root_entry.generation, root_entry.idnum, catalog)


        acro_ref = catalog.raw_get(CD.ACRO_FORM)
        if acro_form_originally_exist and isinstance(acro_ref, IndirectObject):
            incremented_objects[(acro_ref.idnum, acro_ref.generation)] = acro_form
            pdf_reader.cache_indirect_object(acro_ref.generation, acro_ref.idnum, acro_form)

    def _get_cms_object(self, digest: bytes) -> Optional[cms.ContentInfo]:
        """
        Wraps the document hash in a Cryptographic Message Syntax (CMS) structure.

        This conforms to **RFC 5652**. It creates a detached signature (ContentInfo)
        containing the signer's leaf_cert, the signing time, and the signed digest.

        RFC: https://datatracker.ietf.org/doc/html/rfc5652

        :param digest: The SHA-256 hash of the relevant PDF byte ranges.
        :type digest: bytes
        :return: A CMS object populated with the signature data.
        :rtype: cms.ContentInfo or None
        """
        private_key, leaf_cert, cert_chain = self._load_key_and_certificate()
        if private_key is None or leaf_cert is None:
            return None

        cert = x509.Certificate.load(
            leaf_cert.public_bytes(encoding=Encoding.DER)
        )
        all_certificates = [cert]
        if cert_chain:
            for intermediate_cert in cert_chain:
                all_certificates.append(
                    x509.Certificate.load(
                        intermediate_cert.public_bytes(encoding=Encoding.DER)
                    )
                )

        encap_content_info = {
            'content_type': 'data',
            'content': None
        }

        # Define CMS attributes (ContentType, SigningTime, AlgorithmProtection, MessageDigest)
        attrs = cms.CMSAttributes([
            cms.CMSAttribute({
                'type': 'content_type',
                'values': ['data']
            }),
            cms.CMSAttribute({
                'type': 'signing_time',
                'values': [cms.Time({'utc_time': core.UTCTime(self.signing_time)})]
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

        # Sign the attributes
        signed_attrs = private_key.sign(
            attrs.dump(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        # Assemble SignerInfo
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

        # Encapsulate in SignedData
        signed_data = {
            'version': 'v1',
            'digest_algorithms': [algos.DigestAlgorithm({'algorithm': 'sha256'})],
            'encap_content_info': encap_content_info,
            'certificates': all_certificates,
            'signer_infos': [signer_info]
        }

        return cms.ContentInfo({
            'content_type': 'signed_data',
            'content': cms.SignedData(signed_data)
        })

    def _perform_signature(self, pdf_data: bytes) -> bytes:
        """
        Injects the cryptographic signature into the reserved placeholders.

        This method performs the physical byte-level signing:
        1.  **Locate:** Finds the specific ``/ByteRange`` and ``/Contents`` placeholders
            belonging to the *last* signature object in the file.
        2.  **Calculate:** Determines the byte offsets to exclude the signature "hole"
            from the hash calculation.
        3.  **Hash & Sign:** Hashes the valid ranges, generates the CMS object.
        4.  **Inject:** Overwrites the placeholders in the byte stream with the
            calculated ByteRange and the hex-encoded CMS signature.



        :param pdf_data: The complete PDF file bytes containing the empty signature fields.
        :type pdf_data: bytes
        :return: The final signed PDF bytes.
        :rtype: bytes
        :raises ValueError: If placeholders cannot be found or if the generated signature
                            is too large for the reserved buffer.
        """
        pdf_buffer = bytearray(pdf_data)

        # 1. FIND THE TARGET SIGNATURE OBJECT (Last /Type /Sig in file)
        sig_obj_start = pdf_buffer.rfind(b"/Type /Sig")
        if sig_obj_start == -1:
            raise ValueError("No signature placeholder found in the incremental update.")

        # 2. LOCATE PLACEHOLDERS (ByteRange and Contents)
        # Search forward from the object start to find the specific keys belonging to it
        br_key_pos = pdf_buffer.find(b"/ByteRange", sig_obj_start)
        array_start = pdf_buffer.find(b"[", br_key_pos)
        array_end = pdf_buffer.find(b"]", array_start) + 1
        placeholder_len = array_end - array_start

        # Locate Contents hex string < ... >
        c_key_pos = pdf_buffer.find(b"/Contents", sig_obj_start)
        hex_start = pdf_buffer.find(b"<", c_key_pos) + 1  # First byte of hex data
        hex_end = pdf_buffer.find(b">", hex_start)  # Byte after hex data

        # 3. CALCULATE OFFSETS (The "Hole")
        # val1: Start of file
        # val2: Length of first chunk (up to the opening '<')
        # val3: Offset where second chunk starts (after the closing '>')
        # val4: Length of the second chunk (from val3 to EOF)
        val1 = 0
        val2 = hex_start - 1  # The index of the '<'
        val3 = hex_end + 1  # The index after the '>'
        val4 = len(pdf_buffer) - val3

        # # 4. UPDATE BYTERANGE
        # # We format the array and pad with spaces to maintain the exact byte count
        # new_range_str = f"[{val1} {val2} {val3} {val4}]".encode('ascii')
        # if len(new_range_str) > placeholder_len:
        #     raise ValueError("ByteRange string exceeds reserved placeholder space.")
        #
        # # Pad with spaces to fit exact placeholder size
        # pdf_buffer[array_start:array_end] = new_range_str.ljust(placeholder_len, b" ")
        # 4. UPDATE BYTERANGE (Zero-Padding Strategy)
        # Goal: Transform "[0 999...]" into "[0 123 456 0000000789]"
        # This keeps the total length IDENTICAL and valid.

        # 1. Create the first part of the array string: "[0 123 456 "
        # We purposely leave a trailing space after val3 so val4 is separated.
        prefix = f"[{val1} {val2} {val3} ".encode('ascii')
        suffix = b"]"

        # 2. Calculate how much room is left for the last number
        # Total Available - Prefix length - Suffix length
        # e.g., 40 - 15 - 1 = 24 bytes available for val4
        available_len_for_val4 = placeholder_len - len(prefix) - len(suffix)

        if available_len_for_val4 < len(str(val4)):
            raise ValueError(f"Not enough space! Need {len(str(val4))}, have {available_len_for_val4}")

        # 3. Format val4 with leading zeros to fill that space EXACTLY
        # e.g., if we have 10 bytes and val4 is "99", we get "0000000099"
        s_val4 = str(val4).zfill(available_len_for_val4).encode('ascii')

        # 4. Combine them
        new_range_str = prefix + s_val4 + suffix

        # 5. Overwrite the buffer
        # This is now guaranteed to match placeholder_len exactly.
        pdf_buffer[array_start:array_end] = new_range_str

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

        # Fill hole with signature, pad with '0'
        pdf_buffer[hex_start:hex_end] = signature_hex.ljust(max_hex_len, b"0")

        return bytes(pdf_buffer)
