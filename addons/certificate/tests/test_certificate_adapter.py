import base64

from unittest import mock

from odoo.addons.certificate.tools import CertificateAdapter
from odoo.tests import TransactionCase, tagged
from odoo.tools import file_open


class _DummyConnection:
    def __init__(self, ssl_context):
        self.conn_kw = {'ssl_context': ssl_context}


@tagged('post_install', '-at_install')
class TestCertificateAdapter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        certificate_content = file_open('certificate/tests/data/cert.pfx', 'rb').read()
        cls.certificate = cls.env['certificate.certificate'].create({
            'name': 'PKCS12 test certificate',
            'pkcs12_password': 'example',
            'content': base64.b64encode(certificate_content),
        })

    def test_cert_verify_with_certificate_record(self):
        ssl_context = mock.Mock()
        ssl_context._ctx = mock.Mock()
        original_load_cert_chain = ssl_context.load_cert_chain = mock.Mock()
        conn = _DummyConnection(ssl_context)
        adapter = CertificateAdapter()

        with mock.patch('requests.adapters.HTTPAdapter.cert_verify') as cert_verify:
            adapter.cert_verify(conn, 'https://example.com', True, self.certificate)

        cert_verify.assert_called_once_with(conn, 'https://example.com', True, None)
        self.assertEqual(conn.cert_file, self.certificate)
        self.assertIsNone(conn.key_file)
        self.assertNotEqual(ssl_context.load_cert_chain, original_load_cert_chain)

        ssl_context.load_cert_chain(self.certificate)
        ssl_context._ctx.use_certificate.assert_called_once()
        ssl_context._ctx.use_privatekey.assert_called_once()

    def test_cert_verify_with_cert_path_tuple(self):
        ssl_context = mock.Mock()
        original_load_cert_chain = ssl_context.load_cert_chain = mock.Mock()
        conn = _DummyConnection(ssl_context)
        adapter = CertificateAdapter()
        cert_paths = ('/tmp/cert.pem', '/tmp/key.pem')

        with mock.patch('requests.adapters.HTTPAdapter.cert_verify') as cert_verify:
            adapter.cert_verify(conn, 'https://example.com', True, cert_paths)

        cert_verify.assert_called_once_with(conn, 'https://example.com', True, cert_paths)
        self.assertFalse(hasattr(conn, 'cert_file'))
        self.assertFalse(hasattr(conn, 'key_file'))
        ssl_context.load_cert_chain(*cert_paths)
        original_load_cert_chain.assert_called_once_with(*cert_paths)
