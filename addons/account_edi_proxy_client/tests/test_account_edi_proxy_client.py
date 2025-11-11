import base64
from unittest.mock import patch

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo.fields import Selection
from odoo.tests import tagged
from odoo.tools import BinaryBytes

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountEdiProxyUser(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.company_data['company']

        cls.private_key_id = cls.env['certificate.key']._generate_rsa_private_key(
            cls.company,
            name='test_private_key',
        )
        private_content = cls.private_key_id.content.content
        cls.private_key = serialization.load_pem_private_key(private_content, None)

        cls.public_key = cls.private_key.public_key()
        public_content = cls.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        cls.public_key_id = cls.env['certificate.key'].create({
            'name': 'test_public_key',
            'public': True,
            'content': BinaryBytes(public_content),
        })

        # Overcome the abstract selection field `proxy_type` that has no selection
        # We actually dont need it, so we put a placeholder
        with patch.object(Selection, 'convert_to_cache', side_effect=lambda value, record: value):
            cls.base_proxy_user = cls.env['account_edi_proxy_client.user'].create({
                'id_client': 'id_client_test',
                'company_id': cls.company.id,
                'edi_identification': '1234567890',
                'private_key_id': cls.private_key_id.id,
                'edi_mode': 'demo',
                'proxy_type': 'test',
            })

        cls.symmetric_key = Fernet.generate_key()

        sha = hashes.SHA256()
        cls.asymm_encrypted_symmetric_key = cls.public_key.encrypt(
            cls.symmetric_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=sha), algorithm=sha, label=None),
        )

    def test_decrypt_data(self):
        original_text = b"Nothing to see here"
        symm_encrypted_text = Fernet(self.symmetric_key).encrypt(original_text)
        symm_decrypted_text = self.base_proxy_user._decrypt_data(
            base64.b64encode(symm_encrypted_text),
            base64.b64encode(self.asymm_encrypted_symmetric_key),
        )
        self.assertEqual(original_text, symm_decrypted_text)
