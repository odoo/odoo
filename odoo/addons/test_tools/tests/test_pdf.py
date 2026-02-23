# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import hashlib
import io

from unittest.mock import patch
from asn1crypto import algos, cms, core, x509 as asn1x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from odoo.addons.base.tests.files import PDF_RAW
from odoo.tests.common import tagged, TransactionCase
from odoo.tools import pdf
from odoo.tools.misc import file_open
from odoo.tools.pdf import reshape_text
from odoo.tools.pdf.signature import PdfSigner

@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPdf(TransactionCase):
    """ Tests on pdf. """

    def setUp(self):
        super().setUp()
        self.file = PDF_RAW
        self.minimal_reader_buffer = io.BytesIO(self.file)
        self.minimal_pdf_reader = pdf.OdooPdfFileReader(self.minimal_reader_buffer)

    def test_odoo_pdf_file_reader(self):
        attachments = list(self.minimal_pdf_reader.get_attachments())
        self.assertEqual(len(attachments), 0)

        pdf_writer = pdf.PdfFileWriter()
        pdf_writer.clone_reader_document_root(self.minimal_pdf_reader)
        pdf_writer.add_attachment('test_attachment.txt', b'My awesome attachment')
        out = io.BytesIO()
        pdf_writer.write(out)

        r = pdf.OdooPdfFileReader(io.BytesIO(out.getvalue()))
        self.assertEqual(len(list(r.get_attachments())), 1)

    def test_odoo_pdf_file_writer(self):
        attachments = list(self.minimal_pdf_reader.get_attachments())
        self.assertEqual(len(attachments), 0)
        r = self.minimal_pdf_reader

        for count, (name, data) in enumerate([
            ('test_attachment.txt', b'My awesome attachment'),
            ('another_attachment.txt', b'My awesome OTHER attachment'),
        ], start=1):
            pdf_writer = pdf.OdooPdfFileWriter()
            pdf_writer.clone_reader_document_root(r)
            pdf_writer.add_attachment(name, data)
            out = io.BytesIO()
            pdf_writer.write(out)

            r = pdf.OdooPdfFileReader(io.BytesIO(out.getvalue()))
            self.assertEqual(len(list(r.get_attachments())), count)

    def test_odoo_pdf_file_reader_with_owner_encryption(self):
        pdf_writer = pdf.OdooPdfFileWriter()
        pdf_writer.clone_reader_document_root(self.minimal_pdf_reader)

        pdf_writer.add_attachment('test_attachment.txt', b'My awesome attachment')
        pdf_writer.add_attachment('another_attachment.txt', b'My awesome OTHER attachment')

        pdf_writer.encrypt("", "foo")

        with io.BytesIO() as writer_buffer:
            pdf_writer.write(writer_buffer)
            encrypted_content = writer_buffer.getvalue()

        with io.BytesIO(encrypted_content) as reader_buffer:
            pdf_reader = pdf.OdooPdfFileReader(reader_buffer)
            attachments = list(pdf_reader.get_attachments())

        self.assertEqual(len(attachments), 2)

    def test_merge_pdf(self):
        self.assertEqual(len(self.minimal_pdf_reader.pages), 1)

        merged_pdf = pdf.merge_pdf([self.file, self.file])
        merged_reader_buffer = io.BytesIO(merged_pdf)
        merged_pdf_reader = pdf.OdooPdfFileReader(merged_reader_buffer)
        self.assertEqual(len(merged_pdf_reader.pages), 2)
        merged_reader_buffer.close()

    def test_branded_file_writer(self):
        # It's not easy to create a PDF with PyPDF2, so instead we copy PDF with our custom pdf writer
        pdf_writer = pdf.PdfFileWriter()  # BrandedFileWriter
        pdf_writer.clone_reader_document_root(self.minimal_pdf_reader)
        writer_buffer = io.BytesIO()
        pdf_writer.write(writer_buffer)
        branded_content = writer_buffer.getvalue()
        writer_buffer.close()

        # Read the metadata of the newly created pdf.
        reader_buffer = io.BytesIO(branded_content)
        pdf_reader = pdf.PdfFileReader(reader_buffer)
        pdf_info = pdf_reader.metadata
        self.assertEqual(pdf_info['/Producer'], 'Odoo')
        self.assertEqual(pdf_info['/Creator'], 'Odoo')
        reader_buffer.close()

    def tearDown(self):
        super().tearDown()
        self.minimal_reader_buffer.close()

    def test_reshaping_non_arabic_text(self):
        """
        Test that reshaper doesn't alter non-Arabic text.
        """
        english_text = "Hello, I'm just an English text"
        processed_text = reshape_text(english_text)
        self.assertEqual(english_text, processed_text, "English text shouldn't be altered.")

        brazilian_text = "Ayrton Senna foi o melhor piloto de Formula 1 que já existiu"
        processed_brazilian_text = reshape_text(brazilian_text)
        self.assertEqual(brazilian_text, processed_brazilian_text, "Brazilian text shouldn't be altered.")

    def test_reshaping_arabic_text(self):
        """
        Test reshaping is applied properly on Arabic text.
        """
        text = "بث مباشر"
        processed_text = reshape_text(text)
        expected_shapes = ['ﺮ', 'ﺷ', 'ﺎ', 'ﺒ', 'ﻣ', ' ', 'ﺚ', 'ﺑ']

        for i, expected_shape in enumerate(expected_shapes):
            self.assertEqual(processed_text[i], expected_shape)


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSignature(TransactionCase):
    """Tests on signature tool"""

    @classmethod
    def setUpClass(cls):
        super(TestSignature, cls).setUpClass()

        cls.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096
        )

        cert_subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BE"),
            x509.NameAttribute(
                NameOID.STATE_OR_PROVINCE_NAME, "Brabant Wallon"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Grand Rosiere"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Odoo"),
            x509.NameAttribute(NameOID.COMMON_NAME, "odoo.com")
        ])

        cls.certificate = x509.CertificateBuilder().subject_name(
            cert_subject
        ).issuer_name(
            cert_subject
        ).public_key(
            cls.private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) +
            datetime.timedelta(days=10)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False
        ).sign(cls.private_key, hashes.SHA256())

        cls.pdf_path = "base/tests/files/file.pdf"

    def test_odoo_pdf_signer(self):
        fixed_time = datetime.datetime.now(datetime.timezone.utc)
        with file_open(self.pdf_path, "rb") as stream:
            out_stream = io.BytesIO()
            with patch.object(PdfSigner, "_load_key_and_certificate",
                              return_value=(self.private_key, self.certificate)):
                signer = PdfSigner(stream, self.env, signing_time=fixed_time)
                out_stream = signer.sign_pdf()
                if not out_stream:
                    self.skipTest("Could not load the PdfSigner class properly")
            pdf_data = out_stream.getvalue()

            # Retrive the signature content
            sig_field_index = pdf_data.rfind(b"/FT /Sig")
            content_index = pdf_data.find(b"Contents", sig_field_index)
            content_start_index = pdf_data.find(b"<", content_index)
            content_end_index = pdf_data.find(b">", content_index)
            content = pdf_data[content_start_index + 1: content_end_index]

            # Retrieve the computed byte range
            byte_range_index = pdf_data.find(b"ByteRange")
            start_bracket_index = pdf_data.find(b"[", byte_range_index)
            end_bracket_index = pdf_data.find(b"]", start_bracket_index)
            byte_range = pdf_data[start_bracket_index + 1: end_bracket_index].strip().split(b" ")

            # Computing the hash from the resulting document
            hash = hashlib.sha256()
            for i in range(0, len(byte_range), 2):
                hash.update(pdf_data[int(byte_range[i]):int(byte_range[i]) + int(byte_range[i + 1])])
            result_digest = hash.digest()

            cert = asn1x509.Certificate.load(
                self.certificate.public_bytes(encoding=serialization.Encoding.DER))

            # Setting up the content information to assert
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
                    'values': [cms.Time({'utc_time': core.UTCTime(fixed_time)})]
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
                    'values': [result_digest],
                }),
            ])

            signed_attrs = self.private_key.sign(
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

            content_info = cms.ContentInfo({
                'content_type': 'signed_data',
                'content': cms.SignedData(signed_data)
            })

            signature_hex = content_info.dump().hex()
            signature_hex = signature_hex.ljust(8192 * 2, "0")

            self.assertEqual(signature_hex.encode(), content)

