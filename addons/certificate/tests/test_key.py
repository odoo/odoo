import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install')
class TestKey(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.test_key = cls.env['certificate.key'].create({
            'name': 'Test key',
            'content': base64.b64encode(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption())),
        })

    def test_ec_key_generated(self):
        private_key = self.env['certificate.key']._generate_ec_private_key()
        private_key_obj = serialization.load_pem_private_key(base64.b64decode(private_key.pem_key), None)
        self.assertTrue(isinstance(private_key_obj, ec.EllipticCurvePrivateKey))

    def test_rsa_key_generated(self):
        private_key = self.env['certificate.key']._generate_rsa_private_key()
        private_key_obj = serialization.load_pem_private_key(base64.b64decode(private_key.pem_key), None)
        self.assertTrue(isinstance(private_key_obj, rsa.RSAPrivateKey))

    def test_key_loading_wrong_password(self):
        correct_password = 'foobar'
        wrong_password = 'barfoo'
        content = file_open('certificate/tests/data/encrypted_private.key', 'rb').read()
        with self.assertRaises(UserError, msg="The key could not be loaded."):
            self.env['certificate.key'].create({
                'content': base64.b64encode(content),
                'password': wrong_password,
            })
        self.env['certificate.key'].create({
            'content': base64.b64encode(content),
            'password': correct_password,
        })
