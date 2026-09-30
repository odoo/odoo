
import datetime
import hashlib
import io
import os
from unittest.mock import PropertyMock, patch
from asn1crypto import algos, cms, core, x509 as asn1x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from odoo.addons.base.models.res_company import ResCompany
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_open
from odoo.tools.pdf.signature import PdfSigner


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

        cls.pdf_path =  "base/tests/minimal.pdf"

    def test_odoo_pdf_signer(self):
        fixed_time = datetime.datetime.now(datetime.timezone.utc)
        with file_open(self.pdf_path, "rb") as stream:
            out_stream = io.BytesIO()
            with patch.object(PdfSigner, "_load_key_and_certificate", return_value=(self.private_key, self.certificate)):
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
            content = pdf_data[content_start_index+1: content_end_index]
            
            # Retrieve the computed byte range
            byte_range_index = pdf_data.find(b"ByteRange")
            start_bracket_index = pdf_data.find(b"[", byte_range_index)
            end_bracket_index = pdf_data.find(b"]", start_bracket_index)
            byte_range = pdf_data[start_bracket_index + 1: end_bracket_index].strip().split(b" ")

            # Computing the hash from the resulting document
            hash = hashlib.sha256()
            for i in range(0, len(byte_range), 2):
                hash.update(pdf_data[int(byte_range[i]):int(byte_range[i])+int(byte_range[i+1])])
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

