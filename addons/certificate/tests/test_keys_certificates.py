import base64

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from datetime import datetime, timedelta, timezone

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install')
class TestKeysCertificates(TransactionCase):

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
                encryption_algorithm=serialization.NoEncryption()
            )),
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
        cls.test_key_2_private = cls.env['certificate.key'].create({
            'name': 'Test key',
            'content': base64.b64encode(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )),
        })
        cls.test_key_2_public = cls.env['certificate.key'].create({
            'name': 'Test key',
            'content': base64.b64encode(private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )),
        })

    def _generate_keys(self, n=1):
        for _ in range(n):
            yield rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def _search_certificate(self, subject_common_name):
        return self.env['certificate.certificate'].with_context(active_test=False).search([
            ('subject_common_name', '=', subject_common_name),
        ])

    def _build_pem_bundle(self, key, certs):
        return b"".join([
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            *(cert.public_bytes(serialization.Encoding.PEM) for cert in certs),
        ])

    def _build_test_cert(self, subject_cn, issuer_cn, subject_key, issuer_key=None, issuer_pub_key=None, rsa_padding=None):
        if not issuer_key:
            issuer_key = subject_key
        if not issuer_pub_key:
            issuer_pub_key = subject_key.public_key()

        time_now = datetime.now(timezone.utc)
        builder = x509.CertificateBuilder().subject_name(
            x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, subject_cn)]),
        ).issuer_name(
            x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, issuer_cn)]),
        ).public_key(
            subject_key.public_key(),
        ).serial_number(
            x509.random_serial_number(),
        ).not_valid_before(
            time_now - timedelta(days=1),
        ).not_valid_after(
            time_now + timedelta(days=10),
        )

        ski = x509.SubjectKeyIdentifier.from_public_key(subject_key.public_key())
        builder = builder.add_extension(ski, critical=False)

        aki = x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_pub_key)
        builder = builder.add_extension(aki, critical=False)

        # Ed25519/Ed448 sign without a hash. RSA-PSS needs an explicit padding.
        algorithm = None if isinstance(issuer_key, ed25519.Ed25519PrivateKey) else hashes.SHA256()
        extra = {'rsa_padding': rsa_padding} if rsa_padding else {}
        return builder.sign(issuer_key, algorithm, **extra)

    def test_ec_key_generated(self):
        private_key = self.env['certificate.key']._generate_ec_private_key(self.env.company)
        private_key_obj = serialization.load_pem_private_key(base64.b64decode(private_key.pem_key), None)
        self.assertTrue(isinstance(private_key_obj, ec.EllipticCurvePrivateKey))

    def test_rsa_key_generated(self):
        private_key = self.env['certificate.key']._generate_rsa_private_key(self.env.company)
        private_key_obj = serialization.load_pem_private_key(base64.b64decode(private_key.pem_key), None)
        self.assertTrue(isinstance(private_key_obj, rsa.RSAPrivateKey))

    def test_ed25519_key_generated(self):
        private_key = self.env['certificate.key']._generate_ed25519_private_key(self.env.company)
        private_key_obj = serialization.load_pem_private_key(base64.b64decode(private_key.pem_key), None)
        self.assertTrue(isinstance(private_key_obj, ed25519.Ed25519PrivateKey))

    def test_key_loading_wrong_password(self):
        correct_password = 'foobar'
        wrong_password = 'barfoo'
        content = file_open('certificate/tests/data/encrypted_private.key', 'rb').read()
        key = self.env['certificate.key'].create({
            'content': base64.b64encode(content),
            'password': wrong_password,
        })
        self.assertEqual(key.loading_error, 'This key could not be loaded. Either its content or its password is erroneous.')
        key.write({
            'password': correct_password,
        })
        self.assertEqual(key.loading_error, '')

    def test_der_certificate(self):
        certificate = self.env['certificate.certificate'].create({
            'name': 'Test DER Certificate',
            'content': base64.b64encode(self.certificate_1.public_bytes(encoding=serialization.Encoding.DER)),
            'private_key_id': self.test_key_1.id,
        })
        self.assertEqual(certificate.content_format, 'der')

    def test_pem_certificate(self):
        certificate = self.env['certificate.certificate'].create({
            'name': 'Test PEM Certificate',
            'content': base64.b64encode(self.certificate_1.public_bytes(encoding=serialization.Encoding.PEM)),
            'private_key_id': self.test_key_1.id,
        })
        self.assertEqual(certificate.content_format, 'pem')

    def test_pfx_certificate(self):
        certificate = self.env['certificate.certificate'].create({
            'name': 'Test PKCS12 Certificate',
            'pkcs12_password': 'example',
            'content': base64.b64encode(file_open('certificate/tests/data/cert.pfx', 'rb').read()),
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
            'private_key_id': self.test_key_1.id,
        })
        self.assertFalse(expired_cert.is_valid)

    def test_keys_certificate_not_matching(self):
        with self.assertRaises(UserError, msg="The certificate and private key are not compatible."):
            self.env['certificate.certificate'].create({
                'name': "Test PEM Certificate and key don't match",
                'content': base64.b64encode(self.certificate_1.public_bytes(encoding=serialization.Encoding.PEM)),
                'private_key_id': self.test_key_2_private.id,
            })

        with self.assertRaises(UserError, msg="The certificate and public key are not compatible."):
            self.env['certificate.certificate'].create({
                'name': "Test PEM Certificate and key don't match",
                'content': base64.b64encode(self.certificate_1.public_bytes(encoding=serialization.Encoding.PEM)),
                'public_key_id': self.test_key_2_public.id,
            })

    def test_pem_chain_extraction(self):
        """ Test that a PEM bundle is correctly split, CAs are archived, and links are established. """
        root_key, int_key, leaf_key = self._generate_keys(3)

        # Build the chain (Root -> Intermediate -> Leaf)
        root_cert = self._build_test_cert("Test Root CA", "Test Root CA", root_key)
        int_cert = self._build_test_cert("Test Intermediate CA", "Test Root CA", int_key, root_key,
                                         root_key.public_key())
        leaf_cert = self._build_test_cert("Test Leaf", "Test Intermediate CA", leaf_key, int_key,
                                          int_key.public_key())

        bundle_pem = self._build_pem_bundle(leaf_key, [leaf_cert, int_cert, root_cert])

        leaf_record = self.env['certificate.certificate'].create({
            'name': 'Test Chain Upload',
            'content': base64.b64encode(bundle_pem),
        })[0]

        # The intermediate and root should have been created in the background as archived
        int_record = self._search_certificate('Test Intermediate CA')
        root_record = self._search_certificate('Test Root CA')

        self.assertRecordValues(leaf_record, [{
            'active': True,
            'content_format': 'pem',
            'subject_common_name': 'Test Leaf',
            'issuer_cert_id': int_record.id,
        }])
        self.assertRecordValues(int_record, [{'active': False, 'issuer_cert_id': root_record.id}])
        self.assertRecordValues(root_record, [{'active': False, 'issuer_cert_id': False}])

        # Verify the business method returns the full ordered chain
        chain = leaf_record._get_certificate_chain()
        self.assertEqual(chain.ids, [leaf_record.id, int_record.id, root_record.id])

        # Generate a second leaf certificate signed by the same Intermediate CA
        leaf_key_2 = next(self._generate_keys())
        leaf_cert_2 = self._build_test_cert("Test Leaf 2", "Test Intermediate CA", leaf_key_2, int_key,
                                            int_key.public_key())

        # Same Intermediate and Root as the first bundle
        bundle_pem_2 = self._build_pem_bundle(leaf_key_2, [leaf_cert_2, int_cert, root_cert])

        leaf_record_2 = self.env['certificate.certificate'].create({
            'name': 'Test Chain Upload 2',
            'content': base64.b64encode(bundle_pem_2),
        })[0]

        int_records_after = self._search_certificate('Test Intermediate CA')
        root_records_after = self._search_certificate('Test Root CA')

        # Ensure no duplicate CAs were created (count must still be 1)
        self.assertEqual(len(int_records_after), 1, "Duplicate Intermediate CA was created.")
        self.assertEqual(len(root_records_after), 1, "Duplicate Root CA was created.")

        # Assert the second leaf was created successfully and linked to the existing Intermediate CA
        self.assertRecordValues(leaf_record_2, [{
            'subject_common_name': 'Test Leaf 2',
            'issuer_cert_id': int_record.id,
        }])

    def test_pkcs12_chain_extraction(self):
        """ Test that a password-protected PKCS12 bundle is correctly split, CAs are archived, and links are established. """
        root_key, int_key, leaf_key = self._generate_keys(3)

        # Build the chain (Root -> Intermediate -> Leaf)
        root_cert = self._build_test_cert("PKCS12 Root CA", "PKCS12 Root CA", root_key)
        int_cert = self._build_test_cert("PKCS12 Intermediate CA", "PKCS12 Root CA", int_key, root_key,
                                         root_key.public_key())
        leaf_cert = self._build_test_cert("PKCS12 Leaf", "PKCS12 Intermediate CA", leaf_key, int_key,
                                          int_key.public_key())

        # Create a password-protected PKCS12 binary archive
        password = "password"
        p12_der = pkcs12.serialize_key_and_certificates(
            name=b"test_pkcs12_bundle",
            key=leaf_key,
            cert=leaf_cert,
            cas=[int_cert, root_cert],
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
        )

        leaf_record = self.env['certificate.certificate'].create({
            'name': 'Test PKCS12 Chain Upload',
            'content': base64.b64encode(p12_der),
            'pkcs12_password': password,
        })[0]

        # The intermediate and root should have been created in the background as archived
        int_record = self._search_certificate('PKCS12 Intermediate CA')
        root_record = self._search_certificate('PKCS12 Root CA')

        self.assertRecordValues(leaf_record, [{
            'active': True,
            'content_format': 'pkcs12',
            'subject_common_name': 'PKCS12 Leaf',
            'issuer_cert_id': int_record.id,
        }])
        self.assertRecordValues(int_record, [{'active': False, 'issuer_cert_id': root_record.id}])
        self.assertRecordValues(root_record, [{'active': False, 'issuer_cert_id': False}])
        self.assertTrue(leaf_record.private_key_id, "Private key should be auto-computed from the PKCS12 archive")

        # Verify the business method returns the full ordered chain
        chain = leaf_record._get_certificate_chain()
        self.assertEqual(chain.ids, [leaf_record.id, int_record.id, root_record.id])

    def test_certificate_on_update(self):
        """ Test that a password-protected PKCS12 bundle is correctly split after updating the content """
        root_key, int_key, leaf_key = self._generate_keys(3)

        # Build the chain (Root -> Intermediate -> Leaf)
        root_cert = self._build_test_cert("PKCS12 Root CA", "PKCS12 Root CA", root_key)
        int_cert = self._build_test_cert("PKCS12 Intermediate CA", "PKCS12 Root CA", int_key, root_key,
                                         root_key.public_key())
        leaf_cert = self._build_test_cert("PKCS12 Leaf", "PKCS12 Intermediate CA", leaf_key, int_key,
                                          int_key.public_key())

        # Create a password-protected PKCS12 binary archive
        password = 'password'
        p12_der = pkcs12.serialize_key_and_certificates(
            name=b"test_pkcs12_bundle",
            key=leaf_key,
            cert=leaf_cert,
            cas=[int_cert, root_cert],
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
        )

        # Create a temporary certificate with different content
        leaf_record = self.env['certificate.certificate'].create({
            'name': 'Test PKCS12 Certificate',
            'pkcs12_password': 'example',
            'content': base64.b64encode(file_open('certificate/tests/data/cert.pfx', 'rb').read()),
        })
        self.assertEqual(leaf_record.content_format, 'pkcs12')

        # Update the content of the certificate with the chain p12
        leaf_record.write({
            'content': base64.b64encode(p12_der),
            'pkcs12_password': password,
        })

        # The intermediate and root should have been created in the background as archived
        int_record = self._search_certificate('PKCS12 Intermediate CA')
        root_record = self._search_certificate('PKCS12 Root CA')

        self.assertRecordValues(leaf_record, [{
            'content_format': 'pkcs12',
            'issuer_cert_id': int_record.id,
        }])
        self.assertRecordValues(int_record, [{'active': False, 'issuer_cert_id': root_record.id}])
        self.assertRecordValues(root_record, [{'active': False, 'issuer_cert_id': False}])

    def test_unrelated_certificates_filtered(self):
        """ Test that unrelated certificates in a bundle are ignored and not created. """
        leaf_key, unrelated_key = self._generate_keys(2)

        leaf_cert = self._build_test_cert("Test Leaf", "Test Leaf", leaf_key)
        unrelated_cert = self._build_test_cert("Random Unrelated Cert", "Random Unrelated Cert", unrelated_key)

        # Create a PEM bundle with the key, the valid leaf, and an unrelated cert
        bundle_pem = self._build_pem_bundle(leaf_key, [leaf_cert, unrelated_cert])

        leaf_record = self.env['certificate.certificate'].create({
            'name': 'Test Unrelated Upload',
            'content': base64.b64encode(bundle_pem),
        })[0]

        # Ensure the unrelated cert was not created in the database
        unrelated_record = self._search_certificate('Random Unrelated Cert')

        self.assertTrue(leaf_record.private_key_id)
        self.assertFalse(unrelated_record)
        self.assertEqual(len(leaf_record._get_certificate_chain()), 1)
