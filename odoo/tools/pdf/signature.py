import datetime
import hashlib
import io
import uuid
from typing import Any
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

from odoo.addons.base.models.res_company import ResCompany
from odoo.tools.pdf import (
    PdfFileReader,
    IndirectObject,
    ArrayObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    ByteStringObject,
    DecodedStreamObject as StreamObject,
    create_string_object
)

from .incremental_pdf_merge import IncrementalPdfMerge, IndirectObjectsWrapper
from .constants import TrailerKeys as TK, PageAttributes as PG, CatalogDictionary as CD, InteractiveFormDictEntries as IF

_logger = logging.getLogger(__name__)


class _SignatureContentsPlaceholder(ByteStringObject):
    """
    A placeholder for the `/Contents` field in a PDF signature.

    We handle the serialization of the object rather than relying on the pypdf library.
    This prevents the library from changing the format (like encrypting it,
    or changing how the hex is formatted).

    It also records the exact byte location of this placeholder in the file. This way,
    the signing tool knows exactly where to inject the final signature later without
    having to search the entire file to find the right spot.
    """
    RAW_LEN = 16 * 1024  # 16 KiB raw - leaves headroom for LTV / timestamped CMS payloads

    def __new__(cls):
        return bytes.__new__(cls, b"\0" * cls.RAW_LEN)

    def __init__(self):
        super().__init__()
        self.hex_start = None  # absolute offset of the first hex char (after '<')
        self.hex_end = None    # absolute offset of '>' (exclusive end of hex)

    def write_to_stream(self, stream, encryption_key=None):
        stream.write(b"<")
        self.hex_start = stream.tell()
        stream.write(b"0" * self.RAW_LEN * 2)  # hex encoding is 2 chars per raw byte
        self.hex_end = stream.tell()
        stream.write(b">")


class _ByteRangePlaceholder(ArrayObject):
    """ ``/ByteRange`` placeholder for the PDF signature dictionary.

    Reserves a fixed-width slot (``[`` followed by spaces and ``]``) and records its
    absolute offsets in the output stream, so while signing we can fill it directly
    without searching for the bracket.
    """
    SLOT_LEN = 60  # total bytes including '[' and ']' (room for four 10-digit ints + spaces)

    def __init__(self):
        super().__init__()
        self.start = None  # absolute offset of '['
        self.end = None    # absolute offset just past ']'

    def write_to_stream(self, stream, encryption_key=None):
        self.start = stream.tell()
        stream.write(b"[" + b" " * (self.SLOT_LEN - 2) + b"]")
        self.end = stream.tell()


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

    * `ISO 32000-1:2008 <https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf>`_
        (For the general structure of the PDF document).
    * `Digital Signatures in a PDF <https://www.adobe.com/devnet-docs/acrobatetk/tools/DigSig/Acrobat_DigitalSignatures_in_PDF.pdf>`_
        (For the specific structure of the signature dictionary).

    :param pdf_raw: The raw bytes of the original PDF file.
    :param company: The Odoo company record containing the signing certificate/key.
    :param signing_time: Optional datetime to use as the signing timestamp.
                         Defaults to ``datetime.now()``.
    """

    def __init__(self, pdf_raw: bytes, company: ResCompany | None = None, signing_time: datetime.datetime | None = None) -> None:
        self.pdf_raw = pdf_raw
        self.pdf_reader = PdfFileReader(io.BytesIO(pdf_raw), strict=False)
        self.company = company
        self.signing_time = signing_time or datetime.datetime.now(datetime.timezone.utc)

    def pdf_contains_signature(self) -> bool:
        """ Checks if the PDF document contains at least one actively applied digital signature.

        :return: True if at least one applied signature exists, False otherwise.
        """
        form_fields = self.pdf_reader.get_fields()
        if form_fields:
            for field_dict in form_fields.values():
                if field_dict.get("/FT") == "/Sig" and "/V" in field_dict:
                    return True

        return False

    def sign_pdf(self, sig_overlay_pdf: PdfFileReader | None = None, field_name: str | None = None) -> bytes | None:
        """ Inject a cryptographic digital signature into the PDF document.

        Prepares the document by creating a signature field and appending an
        optional visual representation, then finalizes the file with an
        incremental update and cryptographic injection.

        :param sig_overlay_pdf: The parsed PDF widget to overlay as the signature appearance.
        :param field_name: The dictionary name for the signature field. If left as
            ``None``, a unique name of the form ``"Odoo Signature <uuid>"`` is
            generated so re-signing the same document never collides with an existing
            ``/T`` field.
        :return: The signed PDF data, or None if cryptographic keys/dependencies are missing.
        """
        if not self.company or not load_pem_x509_certificates:
            return

        # Encrypted PDFs would end up corrupt: the new objects are written in
        # plaintext while the trailer still carries /Encrypt, so readers reject
        # the result.
        if TK.ENCRYPT in self.pdf_reader.trailer:
            _logger.warning("Skipping PDF signature: encrypted PDFs are not supported.")
            return None

        # Need at least one page to host the signature widget.
        if not self.pdf_reader.pages:
            _logger.warning("Skipping PDF signature: the PDF has no pages.")
            return None

        # Make the field name unique so re-signing the same document does not
        # produce duplicate /T entries (which break form validation in strict viewers).
        if field_name is None:
            field_name = f"Odoo Signature {uuid.uuid4()}"

        incremented_objects = {}

        # 1. Normalize PDF annotations in case it wasn't signed before
        self._normalize_unsigned_pdf_annotations()

        # 2. Prepare the Signature Field Structure
        contents_placeholder, byte_range_placeholder = self._setup_form(
            self.pdf_reader, field_name, incremented_objects, sig_overlay_pdf,
        )

        # 3. Write the Incremental Updated PDF, the placeholders record their own offsets while serializing
        pdf_merger = IncrementalPdfMerge(self.pdf_raw)
        pdf_merger.write_incremented_pdf(self.pdf_reader, incremented_objects)

        # 4. Sign the Document (fill the signature placeholders)
        final_output = pdf_merger.get_output_stream_value()
        signed_pdf_bytes = self._perform_signature(
            final_output, contents_placeholder, byte_range_placeholder,
        )

        return signed_pdf_bytes

    def _normalize_unsigned_pdf_annotations(self):
        """ Prepares an unsigned PDF for sequential digital signing by normalizing annotations.

        If the document is already signed, this method safely exits to preserve the
        existing cryptographic hashes. For unsigned documents, it runs a discrete
        incremental update to force all page ``/Annots`` arrays into indirect objects.

        This structural normalization ensures that when subsequent signatures are
        applied, only the isolated annotation arrays are modified in the XRef table.
        """
        if not self.pdf_contains_signature():
            pdf_merger = IncrementalPdfMerge(self.pdf_raw)
            pdf_merger.normalize_pages_annotations_to_indirect()
            self.pdf_raw = pdf_merger.get_output_stream_value()
            self.pdf_reader = PdfFileReader(io.BytesIO(self.pdf_raw), strict=False)

    def _load_key_and_certificates(self) -> tuple[PrivateKeyTypes | None, Certificate | None, list[Certificate] | None]:
        """ Retrieves and deserializes the private key and certificate from the company record.

        :return: A tuple ``(private_key, certificate)``. Returns ``(None, None)`` if
                 the company has no valid certificate configured.
        """
        certificate = self.company.signing_certificate_id if "signing_certificate_id" in self.company._fields else None
        if not (certificate and certificate.pem_certificate and certificate.private_key_id and certificate.private_key_id.content):
            return None, None, None

        cert_bytes = certificate.pem_certificate.content
        private_key_bytes = certificate.private_key_id.content.content
        all_certs = load_pem_x509_certificates(cert_bytes)

        leaf_cert = all_certs[0]
        cert_chain = all_certs[1:]
        private_key = load_pem_private_key(private_key_bytes, None)

        return private_key, leaf_cert, cert_chain

    def _setup_form(
            self,
            pdf_reader: PdfFileReader,
            field_name: str,
            incremented_objects: dict[tuple[int, int], Any],
            sig_overlay_pdf: PdfFileReader | None = None,
    ) -> tuple[_SignatureContentsPlaceholder, _ByteRangePlaceholder]:
        """ Configure the PDF ``/AcroForm`` and create the required Signature Field dictionaries.

        This method mutates the PDF object graph by injecting:
        1. **AcroForm Dictionary:** Enables forms and sets ``SigFlags`` to 3 (Signatures Exist | Append Only).
        2. **Signature Field:** The core field definition (e.g., ``/FT /Sig``).
        3. **Visual Appearance:** If provided, embeds the ``sig_overlay_pdf`` as a Form XObject widget.
        4. **Signature Value:** A placeholder dictionary (``/Contents`` and ``/ByteRange``) ready for cryptographic injection.

        :param pdf_reader: The reader object holding the current document state.
        :param field_name: The internal name identifier for the signature field.
        :param incremented_objects: Mapping of modified ``(object_id, generation)`` tuples for the incremental save.
        :param sig_overlay_pdf: An optional pre-rendered PDF containing the visual widget overlay.
        """
        indirect_obj_wrapper = IndirectObjectsWrapper()  # A temporary Wrapper for new objects, useful for the indirect traverse
        catalog = pdf_reader.trailer[TK.ROOT]

        # 1. Setup the AcroForm
        acro_form_originally_exist = False
        if CD.ACRO_FORM not in catalog:
            acro_form = DictionaryObject()
            acro_form.update({
                NameObject(IF.SigFlags): NumberObject(3)
            })
            catalog[NameObject(CD.ACRO_FORM)] = indirect_obj_wrapper.add_object(acro_form)
        else:
            acro_form_originally_exist = True
            acro_form = catalog[CD.ACRO_FORM].get_object()
            # Update flags: Allow Append Mode (Bit 2) | Signatures Exist (Bit 1) = 3
            if IF.SigFlags not in acro_form:
                acro_form[NameObject(IF.SigFlags)] = NumberObject(3)
            else:
                current_flags = acro_form[IF.SigFlags]
                acro_form[NameObject(IF.SigFlags)] = NumberObject(int(current_flags) | 3)

        # 2. Define the signature annotation dictionary
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

        # 3. Construct the visual appearance widget (optional)
        signature_overlay = None
        content_stream = None

        if sig_overlay_pdf:
            signature_overlay = sig_overlay_pdf.pages[0]
            content_stream = signature_overlay.get_contents()

        if content_stream is not None:
            # Extract the font dictionaries and formatting from the overlay
            signature_resources = signature_overlay.get(PG.RESOURCES, DictionaryObject())

            # Determine the exact dimensions of the signature block
            calc_width = float(abs(signature_overlay.mediabox.width))
            calc_height = float(abs(signature_overlay.mediabox.height))

            # Calculate absolute coordinates on the first page (Top-Right placement)
            origin = page.mediabox.upper_right
            margin = 20

            x2 = int(float(origin[0]) - margin)
            y2 = int(float(origin[1]) - margin)
            x1 = int(x2 - calc_width)
            y1 = int(y2 - calc_height)

            rect = [x1, y1, x2, y2]

            # Build the Form XObject appearance stream dictionary
            # The /BBox uses local coordinates starting at (0,0) for the internal drawing
            signature_appearance_stream = StreamObject()
            signature_appearance_stream.update({
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Form"),
                NameObject("/BBox"): ArrayObject([
                    NumberObject(0), NumberObject(0),
                    NumberObject(calc_width), NumberObject(calc_height)
                ]),
                NameObject("/Resources"): signature_resources
            })

            # Inject the raw, drawing operations
            signature_appearance_stream._data = content_stream.get_data()

            # Wrap the XObject in an Appearance Dictionary (/AP) under the Normal (/N) state
            signature_appearance = DictionaryObject()
            signature_appearance.update({
                NameObject("/N"): signature_appearance_stream
            })

            # Bind the calculated position (/Rect) and the appearance (/AP) to the Annotation
            signature_annotation.update({
                NameObject("/Rect"): ArrayObject([NumberObject(x) for x in rect]),
                NameObject("/AP"): signature_appearance
            })
        else:
            # Invisible signature (Zero-width rect)
            signature_annotation.update({
                NameObject("/Rect"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0), NumberObject(0)])
            })

        # 4. Prepare the signature object placeholders.
        # The custom placeholder types own their serialization (so the serialization
        # form is independent of the pypdf library) and record their absolute byte
        # offsets so we can fill them directly.
        contents_placeholder = _SignatureContentsPlaceholder()
        byte_range_placeholder = _ByteRangePlaceholder()

        signature_object = DictionaryObject()
        signature_object.update({
            NameObject("/Type"): NameObject("/Sig"),
            NameObject("/Contents"): contents_placeholder,
            NameObject("/ByteRange"): byte_range_placeholder,
            NameObject("/Filter"): NameObject("/Adobe.PPKLite"),
            NameObject("/SubFilter"): NameObject("/adbe.pkcs7.detached"),
            NameObject("/M"): create_string_object(self.signing_time.strftime("D:%Y%m%d%H%M%SZ")),
        })

        # Register objects with the temporary wrapper to get references
        signature_annotation_ref = indirect_obj_wrapper.add_object(signature_annotation)
        signature_object_ref = indirect_obj_wrapper.add_object(signature_object)

        # Link signature value dict to the field dict
        signature_annotation.update({
            NameObject("/V"): signature_object_ref
        })

        # 5. Register the signature annotation in the AcroForm fields, and the page annotations

        # Add to /AcroForm /Fields
        try:
            raw_fields = acro_form.raw_get("/Fields")
        except KeyError:
            raw_fields = None
        if isinstance(raw_fields, IndirectObject):
            fields_array = raw_fields.get_object()
            fields_array.append(signature_annotation_ref)
            raw_id = raw_fields.idnum
            raw_gen = raw_fields.generation
            incremented_objects.setdefault((raw_id, raw_gen), fields_array)
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, raw_gen, raw_id, fields_array)
        else:
            if raw_fields is None:
                raw_fields = ArrayObject()
            raw_fields.append(signature_annotation_ref)
            acro_form[NameObject("/Fields")] = raw_fields

        # Add to Page /Annots
        try:
            raw_annots = page.raw_get(PG.ANNOTS)
        except KeyError:
            raw_annots = None
        if isinstance(raw_annots, IndirectObject):
            annots_array = raw_annots.get_object()
            annots_array.append(signature_annotation_ref)
            raw_id = raw_annots.idnum
            raw_gen = raw_annots.generation
            incremented_objects.setdefault((raw_id, raw_gen), annots_array)
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, raw_gen, raw_id, annots_array)
        else:
            if raw_annots is None:
                raw_annots = ArrayObject()
            raw_annots.append(signature_annotation_ref)
            page[NameObject(PG.ANNOTS)] = raw_annots

            page_ref_id = page.indirect_reference.idnum
            page_ref_gen = page.indirect_reference.generation
            incremented_objects.setdefault((page_ref_id, page_ref_gen), page)
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, page_ref_gen, page_ref_id, page)

        root_entry = pdf_reader.trailer.raw_get(TK.ROOT)
        if isinstance(root_entry, IndirectObject):
            # If Root is indirect, we must explicitly track it for the incremental update
            incremented_objects[root_entry.idnum, root_entry.generation] = catalog
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, root_entry.generation, root_entry.idnum, catalog)

        acro_ref = catalog.raw_get(CD.ACRO_FORM)
        if acro_form_originally_exist and isinstance(acro_ref, IndirectObject):
            incremented_objects[acro_ref.idnum, acro_ref.generation] = acro_form
            IncrementalPdfMerge.update_cached_indirect_object(pdf_reader, acro_ref.generation, acro_ref.idnum, acro_form)

        return contents_placeholder, byte_range_placeholder

    def _get_cms_object(self, digest: bytes) -> cms.ContentInfo | None:
        """ Wraps the document hash in a Cryptographic Message Syntax (CMS) structure.

        This conforms to **RFC 5652**. It creates a detached signature (ContentInfo)
        containing the signer's leaf_cert, the signing time, and the signed digest.

        RFC: https://datatracker.ietf.org/doc/html/rfc5652

        :param digest: The SHA-256 hash of the relevant PDF byte ranges.
        :return: A CMS object populated with the signature data.
        """
        try:
            private_key, leaf_cert, cert_chain = self._load_key_and_certificates()
        except ValueError as e:
            _logger.warning("Skipping PDF signature: Unable to load PEM file. Reason: %s", e)
            return None

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

    def _perform_signature(
            self,
            pdf_data: bytes,
            contents_placeholder: _SignatureContentsPlaceholder,
            byte_range_placeholder: _ByteRangePlaceholder,
    ) -> bytes | None:
        """ Injects the cryptographic signature into the reserved placeholders.

        This method performs the physical byte-level signing:
        1.  **Calculate:** Determines the byte offsets to exclude the signature "hole"
            from the hash calculation, using the offsets recorded by the placeholders
            during serialization.
        2.  **Hash & Sign:** Hashes the valid ranges, generates the CMS object.
        3.  **Inject:** Overwrites the placeholders in the byte stream with the
            calculated ByteRange and the hex-encoded CMS signature.

        :param pdf_data: The complete PDF file bytes containing the empty signature fields.
        :param contents_placeholder: The ``/Contents`` placeholder, which has recorded
            the absolute byte offsets of its hex window during serialization.
        :param byte_range_placeholder: The ``/ByteRange`` placeholder, which has recorded
            the absolute byte offsets of its slot during serialization.
        :return: The final signed PDF bytes.
        :raises ValueError: If the placeholders were not serialized (no recorded
            offsets), or if the generated CMS signature is too large for the reserved
            buffer.
        """
        if contents_placeholder.hex_start is None or byte_range_placeholder.start is None:
            raise ValueError("Signature placeholders were not serialized into the incremental update.")

        pdf_buffer = bytearray(pdf_data)

        # Recover the placeholder slots from the offsets captured at write time
        array_start = byte_range_placeholder.start
        array_end = byte_range_placeholder.end
        placeholder_len = array_end - array_start

        hex_start = contents_placeholder.hex_start
        hex_end = contents_placeholder.hex_end

        # Calculate the signature byte-range values
        # val1: Start of file (always 0)
        # val2: Length of first chunk (up to the opening '<')
        # val3: Offset where second chunk starts (after the closing '>')
        # val4: Length of the second chunk (from val3 to EOF)
        val1 = 0
        val2 = hex_start - 1  # The index of the '<'
        val3 = hex_end + 1  # The index after the '>'
        val4 = len(pdf_buffer) - val3

        # Update the byte-range placeholder and space pad it by transforming  "[0 999...]" into "[0 123 456 789     ]",
        # This keeps the total length IDENTICAL and valid.
        prefix = f"[{val1} {val2} {val3} ".encode('ascii')
        suffix = b"]"

        # Calculate how much room is left for the last number
        # Total Available - Prefix length - Suffix length
        available_len_for_val4 = placeholder_len - len(prefix) - len(suffix)

        if available_len_for_val4 < len(str(val4)):
            raise ValueError(f"Not enough space! Need {len(str(val4))}, have {available_len_for_val4}")

        # Format val4 with trailing spaces
        s_val4 = f"{val4:<{available_len_for_val4}}".encode('ascii')

        # Combine the new byte range
        new_range_str = prefix + s_val4 + suffix

        # Overwrite the buffer
        pdf_buffer[array_start:array_end] = new_range_str

        # We take every byte except the actual signature hex between hex_start-1 and hex_end+1
        data_to_hash = (
                pdf_buffer[val1 : val1 + val2] +
                pdf_buffer[val3 : val3 + val4]
        )
        digest = hashlib.sha256(data_to_hash).digest()

        # Generate and inject the CMS
        cms_content_info = self._get_cms_object(digest)
        if cms_content_info is None:
            return None

        signature_hex = cms_content_info.dump().hex().encode('ascii')

        max_hex_len = hex_end - hex_start
        if len(signature_hex) > max_hex_len:
            raise ValueError(f"CMS signature ({len(signature_hex)}) too large for hole ({max_hex_len})")

        pdf_buffer[hex_start:hex_start + len(signature_hex)] = signature_hex

        return bytes(pdf_buffer)
