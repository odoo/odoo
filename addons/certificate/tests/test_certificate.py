import base64

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta, timezone

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install')
class TestCertificate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.subject = cls.issuer = x509.Name([
            x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "BE"),
            x509.NameAttribute(x509.oid.NameOID.STATE_OR_PROVINCE_NAME, "Brabant wallon"),
            x509.NameAttribute(x509.oid.NameOID.LOCALITY_NAME, "Grand Rosière"),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, "Odoo S.A."),
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "odoo.com"),
        ])

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.test_key_1 = cls.env['certificate.key'].create({
            'name': 'Test key',
            'content': base64.b64encode(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption())),
        })

        cls.certificate_1 = x509.CertificateBuilder().subject_name(
            cls.subject
        ).issuer_name(
            cls.issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc) - timedelta(days=10)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=10)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        ).sign(private_key, hashes.SHA256())

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.test_key_2 = cls.env['certificate.key'].create({
            'name': 'Test key',
            'content': base64.b64encode(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption())),
        })

    def test_der_certificate(self):
        certificate = self.env['certificate.certificate'].create({
            'name': 'Test DER Certificate',
            'content': base64.b64encode(self.certificate_1.public_bytes(encoding=serialization.Encoding.DER)),
            'private_key': self.test_key_1.id,
        })
        self.assertEqual(certificate.content_format, 'der')

    def test_pem_certificate(self):
        certificate = self.env['certificate.certificate'].create({
            'name': 'Test PEM Certificate',
            'content': base64.b64encode(self.certificate_1.public_bytes(encoding=serialization.Encoding.PEM)),
            'private_key': self.test_key_1.id,
        })
        self.assertEqual(certificate.content_format, 'pem')

    def test_pfx_certificate(self):
        certificate = self.env['certificate.certificate'].create({
            'name': 'Test PKCS12 Certificate',
            'pkcs12_password': 'example',
            'content': base64.b64encode(file_open('certificate/demo/cert.pfx', 'rb').read()),
        })
        self.assertEqual(certificate.content_format, 'pkcs12')

    def test_is_valid(self):
        private_key = serialization.load_pem_private_key(
            base64.b64decode(self.test_key_1.pem_key),
            None
        )

        old_certificate = x509.CertificateBuilder().subject_name(
            self.subject
        ).issuer_name(
            self.issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc) - timedelta(days=10)
        ).not_valid_after(
            datetime.now(timezone.utc) - timedelta(days=1)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        ).sign(private_key, hashes.SHA256())

        expired_cert = self.env['certificate.certificate'].create({
            'name': 'Test expired Certificate',
            'content': base64.b64encode(old_certificate.public_bytes(encoding=serialization.Encoding.PEM)),
            'private_key': self.test_key_1.id,
        })
        self.assertFalse(expired_cert.is_valid)

    def test_key_certificate_not_matching(self):
        with self.assertRaises(UserError, msg="The certificate and private key are not compatible."):
            self.env['certificate.certificate'].create({
                'name': "Test PEM Certificate and key don't match",
                'content': base64.b64encode(self.certificate_1.public_bytes(encoding=serialization.Encoding.PEM)),
                'private_key': self.test_key_2.id,
            })
