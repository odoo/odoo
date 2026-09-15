import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


def _rsa_pems_b64():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(private_pem), base64.b64encode(public_pem)


@tagged("post_install", "-at_install")
class TestKeySigning(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Key = cls.env["certificate.key"]
        cls.pem_b64, cls.pub_pem_b64 = _rsa_pems_b64()

    def test_unsupported_hash_rejected(self):
        with self.assertRaises(UserError):
            self.Key._sign_with_key("x", self.pem_b64, hashing_algorithm="md5")

    def test_unloadable_key_rejected(self):
        with self.assertRaises(UserError):
            self.Key._sign_with_key("x", base64.b64encode(b"not a pem"))

    def test_formatting_variants(self):
        wrapped = self.Key._sign_with_key("m", self.pem_b64)
        raw = self.Key._sign_with_key("m", self.pem_b64, formatting="base64")
        self.assertIn(b"\n", wrapped)
        self.assertNotIn(b"\n", raw)

    def test_verify_accepts_a_genuine_rsa_signature(self):
        signature = self.Key._sign_with_key("m", self.pem_b64, formatting="raw")
        self.assertTrue(
            self.Key._execute_signature_verification_with_key(
                "m", signature, self.pub_pem_b64
            ),
        )

    def test_verify_rejects_a_forged_rsa_signature(self):
        signature = self.Key._sign_with_key("m", self.pem_b64, formatting="raw")
        self.assertFalse(
            self.Key._execute_signature_verification_with_key(
                "tampered", signature, self.pub_pem_b64
            ),
        )

    def test_verify_rejects_an_unsupported_hash(self):
        signature = self.Key._sign_with_key("m", self.pem_b64, formatting="raw")
        with self.assertRaises(UserError):
            self.Key._execute_signature_verification_with_key(
                "m",
                signature,
                self.pub_pem_b64,
                signature_algorithm="md5",
            )


@tagged("post_install", "-at_install")
class TestKeyCryptoOperations(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Key = cls.env["certificate.key"]

        ed_key = ed25519.Ed25519PrivateKey.generate()
        cls.ed_private = cls.Key.create(
            {
                "name": "Ed25519 private",
                "content": base64.b64encode(
                    ed_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                ),
            },
        )
        cls.ed_public = cls.Key.create(
            {
                "name": "Ed25519 public",
                "content": base64.b64encode(
                    ed_key.public_key().public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                ),
            },
        )

        cls.rsa_crypto_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        cls.rsa_private = cls.Key.create(
            {
                "name": "RSA private",
                "content": base64.b64encode(
                    cls.rsa_crypto_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                ),
            },
        )

        cls.rsa_encrypted_crypto_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        cls.rsa_private_encrypted = cls.Key.create(
            {
                "name": "RSA private (password-protected)",
                "content": base64.b64encode(
                    cls.rsa_encrypted_crypto_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.BestAvailableEncryption(
                            b"hunter2"
                        ),
                    )
                ),
                "password": "hunter2",
            },
        )

    def test_sign_requires_private_key(self):
        with self.assertRaises(UserError):
            self.ed_public._sign("payload")

    def test_verify_requires_public_key(self):
        with self.assertRaises(UserError):
            self.ed_private._execute_signature_verification("payload", b"whatever")

    def test_ed25519_sign_verify_round_trip(self):
        signature = base64.b64decode(
            self.ed_private._sign("payload", formatting="base64")
        )
        self.assertTrue(
            self.ed_public._execute_signature_verification("payload", signature)
        )
        self.assertFalse(
            self.ed_public._execute_signature_verification("tampered", signature)
        )

    def test_rsa_decrypt_round_trip(self):
        ciphertext = self.rsa_crypto_key.public_key().encrypt(
            b"secreto",
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        self.assertEqual(self.rsa_private._decrypt(ciphertext), "secreto")

    def test_rsa_decrypt_round_trip_with_password_protected_key(self):
        ciphertext = self.rsa_encrypted_crypto_key.public_key().encrypt(
            b"secreto",
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        self.assertEqual(self.rsa_private_encrypted._decrypt(ciphertext), "secreto")

    def test_decrypt_guards(self):
        with self.assertRaises(UserError):
            self.ed_public._decrypt(b"x")
        with self.assertRaises(UserError):
            self.rsa_private._decrypt(b"x", hashing_algorithm="md5")
        with self.assertRaises(UserError):
            self.ed_private._decrypt(b"x")


@tagged("post_install", "-at_install")
class TestKeyDerLoading(TransactionCase):
    """_get_pem_key_and_metadata's DER branches had zero test coverage: PEM- and
    PKCS12-shaped fixtures exercised the loader everywhere else, but
    never a raw DER private or public key."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Key = cls.env["certificate.key"]
        cls.crypto_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def test_der_private_key_is_loaded_as_private(self):
        key = self.Key.create(
            {
                "name": "DER private",
                "content": base64.b64encode(
                    self.crypto_key.private_bytes(
                        encoding=serialization.Encoding.DER,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                ),
            }
        )
        self.assertFalse(key.public)
        self.assertFalse(key.loading_error)

    def test_der_public_key_is_loaded_as_public(self):
        key = self.Key.create(
            {
                "name": "DER public",
                "content": base64.b64encode(
                    self.crypto_key.public_key().public_bytes(
                        encoding=serialization.Encoding.DER,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                ),
            }
        )
        self.assertTrue(key.public)
        self.assertFalse(key.loading_error)

    def test_der_private_key_sign_verify_round_trip(self):
        private_key = self.Key.create(
            {
                "name": "DER private (sign)",
                "content": base64.b64encode(
                    self.crypto_key.private_bytes(
                        encoding=serialization.Encoding.DER,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                ),
            }
        )
        public_key = self.Key.create(
            {
                "name": "DER public (verify)",
                "content": base64.b64encode(
                    self.crypto_key.public_key().public_bytes(
                        encoding=serialization.Encoding.DER,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                ),
            }
        )
        signature = base64.b64decode(private_key._sign("payload", formatting="base64"))
        self.assertTrue(
            public_key._execute_signature_verification("payload", signature)
        )
