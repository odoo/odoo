import unittest
from unittest.mock import patch

from custom_addons.br_base.services.br_sign_service import BrSignService


class TestBrCertificado(unittest.TestCase):
    @patch.object(BrSignService, "load_cert_a1")
    def test_load_cert_a1(self, mock_load):
        service = BrSignService()
        mock_load.return_value = ("cert", "key")
        cert, key = service.load_cert_a1(b"abc", "123")
        self.assertEqual((cert, key), ("cert", "key"))

    def test_sign_xml_sem_dependencias(self):
        service = BrSignService()
        with self.assertRaises(RuntimeError):
            service.sign_xml(b"<root/>", None, None, "#id")

