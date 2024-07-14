import base64

from cryptography import x509
from cryptography.hazmat.primitives import asymmetric, hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from datetime import datetime, timedelta

from .common import TestL10nClEdiCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nClCertificate(TestL10nClEdiCommon):

    def test_l10n_cl_certificate_get_data(self):
        subject_cn = "Foo"
        subject_serial_number = "12345"

        cert_serial_number = 67890
        cert_not_valid_before = datetime.now()
        cert_not_valid_after = datetime.now() + timedelta(days=365)

        private_key = asymmetric.rsa.generate_private_key(public_exponent=65537, key_size=2048)

        cert = x509.CertificateBuilder(
            subject_name=x509.Name([
                x509.NameAttribute(x509.NameOID.COMMON_NAME, subject_cn),
                x509.NameAttribute(x509.NameOID.SERIAL_NUMBER, subject_serial_number),
            ]),
            issuer_name=x509.Name([]),
            public_key=private_key.public_key(),
            serial_number=cert_serial_number,
            not_valid_before=cert_not_valid_before,
            not_valid_after=cert_not_valid_after,
        ).sign(private_key, hashes.SHA256())

        passphrase = b"foo"

        pkcs12_data = pkcs12.serialize_key_and_certificates(
            name=b"Foo",
            key=private_key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
        )

        self.certificate.write({
            "signature_key_file": base64.b64encode(pkcs12_data),
            "signature_pass_phrase": passphrase,
        })

        origin_cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
        origin_private_key = private_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )

        cert_pem, cert, private_key = self.certificate._get_data()

        self.assertEqual(cert_pem, b"".join(origin_cert_pem.strip().split(b"\n")[1:-1]))
        self.assertEqual(cert.get_notBefore(), cert_not_valid_before.strftime("%Y%m%d%H%M%SZ").encode())
        self.assertEqual(cert.get_notAfter(), cert_not_valid_after.strftime("%Y%m%d%H%M%SZ").encode())
        self.assertEqual(cert.get_serial_number(), cert_serial_number)
        self.assertEqual(cert.get_subject().CN, subject_cn)
        self.assertEqual(cert.get_subject().serialNumber, subject_serial_number)
        self.assertEqual(private_key, origin_private_key)
