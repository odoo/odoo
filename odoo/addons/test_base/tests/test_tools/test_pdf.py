# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import hashlib
import io

from unittest.mock import patch
from asn1crypto import algos, cms, tsp, x509 as asn1x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from odoo.addons.base.tests.files import PDF_RAW, KIDS_PDF_RAW
from odoo.tests.common import tagged, TransactionCase
from odoo.tools import pdf
from odoo.tools.misc import file_open
from odoo.tools.pdf import reshape_text
from odoo.tools.pdf.incremental_pdf_merge import IncrementalPdfMerge, get_page_media_box
from odoo.tools.pdf.signature import (
    PdfSigner,
    SignaturePolicy,
    build_cms_signature,
    build_signed_attributes,
    certificate_common_name,
    next_signature_appearance_origin,
)


def verify_pdf_signatures(pdf_data, public_key, signer_certificate_der=None, expected_chain_length=None):
    """ Verifies every applied signature in the document: recomputes the ``/ByteRange``
    digest, matches it against the ``message_digest`` attribute, checks the certificate
    binding attribute, and verifies the RSA signature over the signed attributes.

    :param pdf_data: The complete PDF bytes.
    :param public_key: The signer's public key, to verify the signature values.
    :param signer_certificate_der: When given, the signing-certificate-v2 attribute must
        hash this certificate.
    :param expected_chain_length: When given, the number of certificates that must be
        embedded in each CMS.
    :return: The number of verified signatures.
    :raises AssertionError, InvalidSignature: If any check fails.
    """
    reader = pdf.PdfFileReader(io.BytesIO(pdf_data), strict=False)
    verified = 0
    for field in (reader.get_fields() or {}).values():
        if field.get('/FT') != '/Sig' or not field.get('/V'):
            continue
        sig_dict = field['/V'].get_object()

        digest = hashlib.sha256()
        byte_range = [int(value) for value in sig_dict['/ByteRange']]
        for start, length in zip(byte_range[0::2], byte_range[1::2]):
            digest.update(pdf_data[start:start + length])

        signed_data = cms.ContentInfo.load(bytes(sig_dict['/Contents']))['content']
        signer_info = signed_data['signer_infos'][0]
        signed_attrs = signer_info['signed_attrs']
        attr_map = {attr['type'].native: attr['values'] for attr in signed_attrs}

        assert attr_map['message_digest'][0].native == digest.digest()
        if signer_certificate_der is not None:
            cert_ids = attr_map['signing_certificate_v2'][0]['certs']
            assert cert_ids[0]['cert_hash'].native == hashlib.sha256(signer_certificate_der).digest()
        if expected_chain_length is not None:
            assert len(signed_data['certificates']) == expected_chain_length
        # raises InvalidSignature if the signature does not match
        public_key.verify(
            signer_info['signature'].native,
            signed_attrs.untag().dump(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        verified += 1
    return verified

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

    def test_odoo_pdf_file_reader_with_nested_attachments(self):
        reader_buffer = io.BytesIO(KIDS_PDF_RAW)
        pdf_reader = pdf.OdooPdfFileReader(reader_buffer, strict=False)
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
            with patch.object(PdfSigner, "_load_key_and_certificates",
                              return_value=(self.private_key, self.certificate, None)):
                signer = PdfSigner(stream.read(), self.env, signing_time=fixed_time)
                out_stream = signer.sign_pdf()
                if not out_stream:
                    self.skipTest("Could not load the PdfSigner class properly")
            pdf_data = out_stream

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
                cms.CMSAttribute({
                    'type': tsp.CMSAttributeType('signing_certificate_v2'),
                    'values': [tsp.SigningCertificateV2({
                        'certs': [tsp.ESSCertIDv2({
                            'hash_algorithm': algos.DigestAlgorithm({'algorithm': 'sha256'}),
                            'cert_hash': hashlib.sha256(cert.dump()).digest(),
                        })],
                    })],
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
            signature_hex = signature_hex.ljust(16 * 1024 * 2, "0")

            self.assertEqual(signature_hex.encode(), content)

    def _verify_pdf_signatures(self, pdf_data):
        return verify_pdf_signatures(
            pdf_data, self.certificate.public_key(),
            signer_certificate_der=self.certificate.public_bytes(serialization.Encoding.DER))

    def test_prepare_finalize_matches_sign_pdf(self):
        """ The split prepare/finalize path with an externally computed signature must
        produce the exact bytes of the one-shot local signing path. """
        fixed_time = datetime.datetime.now(datetime.timezone.utc)
        field_name = "Test Signature"
        with file_open(self.pdf_path, "rb") as stream:
            raw = stream.read()

        with patch.object(PdfSigner, "_load_key_and_certificates",
                          return_value=(self.private_key, self.certificate, None)):
            signed_direct = PdfSigner(raw, self.env, signing_time=fixed_time).sign_pdf(field_name=field_name)

        signer = PdfSigner(raw, signing_time=fixed_time)
        prepared = signer.write_signature_placeholder(field_name=field_name)
        cert = asn1x509.Certificate.load(self.certificate.public_bytes(serialization.Encoding.DER))
        signed_attrs = build_signed_attributes(prepared.digest, cert)
        # What an external signing service returns: a raw signature over the attributes
        signature = self.private_key.sign(signed_attrs.dump(), padding.PKCS1v15(), hashes.SHA256())
        signed_split = signer.fill_signature_placeholder(prepared, build_cms_signature(signed_attrs, signature, cert).dump())

        self.assertEqual(signed_split, signed_direct)
        self.assertEqual(self._verify_pdf_signatures(signed_split), 1)

    def test_signed_attributes_signature_policy(self):
        """ The signature-policy-identifier attribute is present only when a policy is
        supplied, and carries its oid, (empty) hash and uri. """
        cert = asn1x509.Certificate.load(self.certificate.public_bytes(serialization.Encoding.DER))
        digest = hashlib.sha256(b"pdf").digest()

        plain = {attr['type'].native for attr in build_signed_attributes(digest, cert)}
        self.assertNotIn('signature_policy_identifier', plain)

        policy = SignaturePolicy(
            oid='1.3.6.1.4.1.49274.1.1.7.2.0',
            uri='https://www.itsme.be/legal/document-repository')
        # reload from DER so the assertions run on the encoded form, not the source object
        attrs = cms.CMSAttributes.load(build_signed_attributes(digest, cert, policy).dump())
        by_type = {attr['type'].native: attr for attr in attrs}
        self.assertIn('signature_policy_identifier', by_type)
        policy_id = by_type['signature_policy_identifier']['values'][0]
        self.assertEqual(policy_id['sig_policy_id'].native, policy.oid)
        self.assertEqual(policy_id['sig_policy_hash']['hash_value'].native, b'')
        self.assertEqual(policy_id['sig_policy_qualifiers'][0]['qualifier'].native, policy.uri)

    def _appearance_pdf(self, width, height):
        """ A one page PDF of the given size, standing in for a signature appearance. """
        writer = pdf.PdfFileWriter()
        writer.add_blank_page(width=width, height=height)
        stream = io.BytesIO()
        writer.write(stream)
        return pdf.PdfFileReader(stream, strict=False)

    def test_next_signature_appearance_origin(self):
        """ Appearances fill a row from the left, then open the row above. One that cannot
        fit anywhere falls back to the bottom left corner. """
        margin, gap = 20, 6
        box = get_page_media_box(pdf.PdfFileReader(io.BytesIO(PDF_RAW), strict=False).pages[0])
        left, bottom = float(box.left) + margin, float(box.bottom) + margin
        right = float(box.right) - margin
        appearance = self._appearance_pdf(200, 50)

        def visible_signature_rects_patch(rects):
            """ What the page is already signed with. """
            return patch('odoo.tools.pdf.signature.visible_signature_rects', lambda page: rects)

        with visible_signature_rects_patch([]):
            self.assertEqual(next_signature_appearance_origin(PDF_RAW, appearance), (left, bottom))

        # one appearance is there, so the next one goes to its right, after the gap
        with visible_signature_rects_patch([(left, bottom, left + 200, bottom + 50)]):
            self.assertEqual(
                next_signature_appearance_origin(PDF_RAW, appearance), (left + 200 + gap, bottom))

        # the row has no room left, so the next one opens the row above it
        with visible_signature_rects_patch([(left, bottom, right - 100, bottom + 50)]):
            self.assertEqual(
                next_signature_appearance_origin(PDF_RAW, appearance), (left, bottom + 50 + gap))

        # wider than the page. No row can ever hold it, so it covers the bottom left
        with visible_signature_rects_patch([]):
            self.assertEqual(
                next_signature_appearance_origin(PDF_RAW, self._appearance_pdf(2000, 50)), (left, bottom))

    def test_signature_policy_from_policy_data(self):
        """ A policy is built from what a signing service declares, and nothing at all
        when it declares none. """
        self.assertIsNone(SignaturePolicy.from_policy_data(None))
        self.assertIsNone(SignaturePolicy.from_policy_data({}))

        policy = SignaturePolicy.from_policy_data({
            'oid': '1.2.3',
            'uri': 'https://policy.example',
            'digest': base64.b64encode(b'hash').decode(),
        })
        self.assertEqual(policy.oid, '1.2.3')
        self.assertEqual(policy.uri, 'https://policy.example')
        self.assertEqual(policy.digest, b'hash')
        self.assertEqual(policy.digest_algorithm, 'sha256')

    def test_certificate_common_name(self):
        chain = self.certificate.public_bytes(serialization.Encoding.PEM)
        common_name = self.certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        self.assertEqual(certificate_common_name(chain), common_name)
        self.assertIsNone(certificate_common_name(b'not a certificate'))

    def test_incremental_double_signature(self):
        """ A second signature must not touch the bytes covered by the first one, and
        both signatures must remain verifiable. """
        with file_open(self.pdf_path, "rb") as stream:
            raw = stream.read()

        with patch.object(PdfSigner, "_load_key_and_certificates",
                          return_value=(self.private_key, self.certificate, None)):
            first = PdfSigner(raw, self.env).sign_pdf(field_name="Signer 1")
            second = PdfSigner(first, self.env).sign_pdf(field_name="Signer 2")

        self.assertEqual(second[:len(first)], first)
        self.assertEqual(self._verify_pdf_signatures(second), 2)

    def _build_nested_xobject_overlay(self, width, height):
        """ Builds a one-page PDF whose content draws through two levels of nested
        Form XObjects: page contents -> /Outer Do -> /Inner Do. """
        writer = pdf.PdfFileWriter()
        page = writer.add_blank_page(width=width, height=height)
        bbox = pdf.ArrayObject([pdf.NumberObject(value) for value in (0, 0, width, height)])

        inner = pdf.DecodedStreamObject()
        inner.set_data(b"0 0 1 rg 10 10 100 50 re f")
        inner.update({
            pdf.NameObject("/Type"): pdf.NameObject("/XObject"),
            pdf.NameObject("/Subtype"): pdf.NameObject("/Form"),
            pdf.NameObject("/BBox"): bbox,
        })

        outer = pdf.DecodedStreamObject()
        outer.set_data(b"q /Inner Do Q")
        outer.update({
            pdf.NameObject("/Type"): pdf.NameObject("/XObject"),
            pdf.NameObject("/Subtype"): pdf.NameObject("/Form"),
            pdf.NameObject("/BBox"): bbox,
            pdf.NameObject("/Resources"): pdf.DictionaryObject({
                pdf.NameObject("/XObject"): pdf.DictionaryObject({
                    pdf.NameObject("/Inner"): writer._add_object(inner),
                }),
            }),
        })

        contents = pdf.DecodedStreamObject()
        contents.set_data(b"q /Outer Do Q")
        page[pdf.NameObject("/Contents")] = writer._add_object(contents)
        page[pdf.NameObject("/Resources")] = pdf.DictionaryObject({
            pdf.NameObject("/XObject"): pdf.DictionaryObject({
                pdf.NameObject("/Outer"): writer._add_object(outer),
            }),
        })

        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue()

    def test_merge_nested_form_xobjects_and_sign(self):
        """ Stress the incremental merge object sweep with an overlay containing nested
        Form XObjects, then sign the result and verify the signature. """
        writer = pdf.PdfFileWriter()
        writer.add_blank_page(width=612, height=792)
        base_buffer = io.BytesIO()
        writer.write(base_buffer)
        raw = base_buffer.getvalue()
        overlay_raw = self._build_nested_xobject_overlay(612, 792)

        merger = IncrementalPdfMerge(raw)
        merger.merge_pdf_regions_as_annotations(
            pdf.PdfFileReader(io.BytesIO(overlay_raw), strict=False),
            {0: [(10, 10, 110, 60)]},
            annotations_title="nested")
        merged = merger.get_output_stream_value()

        # The increment only appended bytes
        self.assertEqual(merged[:len(raw)], raw)

        # The region is exposed at its own coordinates, so /BBox and /Rect match
        reader = pdf.PdfFileReader(io.BytesIO(merged), strict=False)
        stamp = reader.pages[0]["/Annots"][-1].get_object()
        self.assertEqual(stamp["/Subtype"], "/Stamp")
        self.assertEqual([float(coordinate) for coordinate in stamp["/Rect"]], [10, 10, 110, 60])
        appearance = stamp["/AP"]["/N"].get_object()
        self.assertEqual([float(coordinate) for coordinate in appearance["/BBox"]], [10, 10, 110, 60])
        self.assertEqual(appearance.get_data(), b"q /X0 Do Q")

        # The whole nested XObject graph survived the merge remapping
        page_overlay = appearance["/Resources"]["/XObject"]["/X0"].get_object()
        outer = page_overlay["/Resources"]["/XObject"]["/Outer"].get_object()
        inner = outer["/Resources"]["/XObject"]["/Inner"].get_object()
        self.assertEqual(page_overlay.get_data(), b"q /Outer Do Q")
        self.assertEqual(outer.get_data(), b"q /Inner Do Q")
        self.assertEqual(inner.get_data(), b"0 0 1 rg 10 10 100 50 re f")

        # The merged document can still be signed and verified
        with patch.object(PdfSigner, "_load_key_and_certificates",
                          return_value=(self.private_key, self.certificate, None)):
            signed = PdfSigner(merged, self.env).sign_pdf()
        self.assertEqual(self._verify_pdf_signatures(signed), 1)
