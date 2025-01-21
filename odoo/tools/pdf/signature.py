import base64
import datetime
import io
from typing import Optional
from asn1crypto import cms, algos, core, x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.x509 import Certificate

from odoo import _
from odoo.addons.base.models.res_company import ResCompany
from odoo.addons.base.models.res_users import ResUsers
from odoo.tools.pdf import BooleanObject, PdfReader, PdfWriter, ArrayObject, ByteStringObject, DictionaryObject, NameObject, NumberObject, create_string_object, DecodedStreamObject as StreamObject


class PdfSigner:
    """Class that defines methods uses in the signing process of pdf documents"""

    def __init__(self, stream: io.BytesIO, company: Optional[ResCompany] = None) -> None:
        reader = PdfReader(stream)
        self.writer = PdfWriter()
        self.writer.clone_document_from_reader(reader)

        self.company = company

    def sign_pdf(self, visible_signature: bool = False, field_name: str = "Odoo Signature", signer: Optional[ResUsers] = None) -> Optional[io.BytesIO]:
        """Signs the pdf document using a PdfWriter object

        Returns:
            Optional[io.BytesIO]: the resulting output stream after the signature has been performed, or None in case of error
        """
        if self.company is None:
            return None

        _, sig_field_value = self._setup_form(visible_signature, field_name,  signer)

        if not self._perform_signature(sig_field_value):
            return None

        out_stream = io.BytesIO()
        self.writer.write_stream(out_stream)
        return out_stream

    def _load_key_and_certificate(self) -> Optional[tuple[Optional[PrivateKeyTypes], Optional[Certificate], list[Certificate]]]:
        """Loads the private key

        Returns:
            Optional[PrivateKeyTypes]: a private key object, or None if the key couldn't be loaded.
        """
        if "signing_certificate" not in self.company or not self.company.signing_certificate:
            return None, None, []
        cert_bytes = base64.decodebytes(self.company.signing_certificate)
        password_bytes = self.company.signing_certificate_password.encode() if self.company.signing_certificate_password else None
        return load_key_and_certificates(cert_bytes, password_bytes)

    def _setup_form(self, visible_signature: bool, field_name: str, signer: Optional[ResUsers] = None) -> tuple[DictionaryObject, DictionaryObject] | None:
        """Creates the /AcroForm and populates it with the appropriate field for the signature

        Args:
            field_name (str): the name of the signature field

        Returns:
            tuple[DictionaryObject, DictionaryObject]: a tuple containing the signature field and the signature content
        """
        form = None
        fields = None
        if "/AcroForm" not in self.writer._root_object:
            fields = ArrayObject()

            form = DictionaryObject()
            form.update({
                NameObject("/Fields"): fields,
                NameObject("/SigFlags"): NumberObject(3)
            })
            form_ref = self.writer._add_object(form)

            self.writer._root_object.update({
                NameObject("/AcroForm"): form_ref
            })
        else:
            form = self.writer._root_object["/AcroForm"].get_object()
            
            if "/Fields" not in self.writer._root_object:
                fields = ArrayObject()
            else:
                fields = self.writer._root_object["/Fields"].get_object()

            form.update({
                NameObject("/Fields"): fields,
                NameObject("/SigFlags"): NumberObject(3)
            })

        # Assigning the newly created field to a page
        page = self.writer.pages[0]

        # Setting up the signature field properties
        signature_field = DictionaryObject()
        signature_field.update({
            NameObject("/FT"): NameObject("/Sig"),
            NameObject("/T"): create_string_object(field_name),
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/F"): NumberObject(132),
            NameObject("/P"): page.indirect_reference,
        })

        
        if visible_signature:
            origin = page.mediabox.upper_right
            rect_size = (200, 20)
            padding = 5
            rect = [
                origin[0] - rect_size[0] - padding,
                origin[1] - rect_size[1] - padding,
                origin[0] - padding,
                origin[1] - padding
            ]

            stream = StreamObject()
            stream.update({
                NameObject("/BBox"): self._create_number_array_object([0, 0, rect_size[0], rect_size[1]]),
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
            content = "Digitally signed"
            content = create_string_object(f'{content} by {signer.name} <{signer.email}>') if signer is not None else create_string_object(content)
            stream._data = f"q 0.5 0 0 0.5 0 0 cm BT /F1 12 Tf 0 TL 0 10 Td ({content}) Tj ET Q".encode()
            signature_appearence = DictionaryObject()
            signature_appearence.update({
                NameObject("/N"): stream
            })
            signature_field.update({
                NameObject("/AP"): signature_appearence,
            })
        else:
            rect = [0,0,0,0]

        signature_field.update({
            NameObject("/Rect"): self._create_number_array_object(rect)
        })

        

        # Setting up the actual signature contents with placeholders for /Contents and /ByteRange
        signature_field_value = DictionaryObject()
        signature_field_value.update({
            NameObject("/Contents"): ByteStringObject(b"\0" * 8192),
            NameObject("/ByteRange"): self._create_number_array_object([0, 0, 0, 0]),
            NameObject("/Type"): NameObject("/Sig"),
            NameObject("/Filter"): NameObject("/Adobe.PPKLite"),
            NameObject("/SubFilter"): NameObject("/adbe.pkcs7.detached"),
            NameObject("/M"): create_string_object(datetime.datetime.now(datetime.UTC).strftime("D:%Y%m%d%H%M%S")),
        })
        signature_field_ref = self.writer._add_object(signature_field)
        signature_field_value_ref = self.writer._add_object(signature_field_value)

        signature_field.update({
            NameObject("/V"): signature_field_value_ref
        })

        fields.append(signature_field_ref)


        if "/Annots" not in page:
            page[NameObject("/Annots")] = ArrayObject()
        page[NameObject("/Annots")].append(signature_field_ref)

        return signature_field, signature_field_value

    def _get_cms_object(self, digest: bytes) -> Optional[cms.ContentInfo]:
        """Creates an object that follows the Cryptographic Message Syntax(CMS)

        Args:
            digest (bytes): the digest of the document in bytes

        Returns:
            cms.ContentInfo: a CMS object containing the information of the signature
        """
        private_key, certificate, _ = self._load_key_and_certificate()
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
                'values': [cms.Time({'utc_time': core.UTCTime(datetime.datetime.now(datetime.UTC))})]
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

    def _perform_signature(self, sig_field_value: DictionaryObject) -> bool:
        """Creates the actual signature content and populate /ByteRange and /Contents properties with meaningful content.

        Args:
            sig_field_value (DictionaryObject): the value (/V) of the signature field which needs to be modified
        """
        pdf_data = self._get_document_data()

        # Computation of the location of the last inserted contents for the signature field
        signature_field_pos = pdf_data.rfind(b"/FT /Sig")
        contents_field_pos = pdf_data.find(b"Contents", signature_field_pos)

        placeholder_start = contents_field_pos + 9
        placeholder_end = placeholder_start + len(b"\0" * 8192) * 2 + 2

        # Replacing the placeholder byte range with the actual range 
        # that will be used to compute the document digest
        placeholder_byte_range = sig_field_value.get("/ByteRange")
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

    def _get_document_data(self):
        """Retrieves the bytes of the document from the writer"""
        output_stream = io.BytesIO()
        self.writer.write_stream(output_stream)
        return output_stream.getvalue()


    def _correct_byte_range(self, old_range: list[int], new_range: list[int], base_pdf_len: int) -> list[int]:
        """Corrects the last value of the new byte range

        Args:
            old_range (list[int]): the previous byte range
            new_range (list[int]): the new byte range
            base_pdf_len (int): the base length of the pdf, before insertion of the actual byte range

        Returns:
            list[int]: the corrected byte range
        """
        current_len = len(str(old_range))
        corrected_len = len(str(new_range))
        diff = corrected_len - current_len

        if diff == 0:
            return new_range
        else:
            corrected_range = new_range.copy()
            corrected_range[-1] = abs((base_pdf_len + diff) - new_range[-2])
            return self._correct_byte_range(new_range, corrected_range, base_pdf_len)


    def _compute_digest_from_byte_range(self, data: bytes, byte_range: list[int]) -> bytes:
        """Computes the digest of the data from a byte range. Uses SHA256 algorithm to compute the hash.

        Args:
            document (bytes): the data in bytes
            byte_range (list[int]): the byte range used to compute the digest

        Returns:
            bytes: the computed digest
        """
        hashed = hashes.Hash(hashes.SHA256())
        for i in range(0, len(byte_range), 2):
            hashed.update(data[byte_range[i]:byte_range[i] + byte_range[i+1]])
        return hashed.finalize()

    def _create_number_array_object(self, array: list[int]) -> ArrayObject:
        return ArrayObject([NumberObject(item) for item in array])
