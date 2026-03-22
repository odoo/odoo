import unittest
from unittest.mock import Mock, patch

from custom_addons.br_base.services.br_cep_service import fetch_cep


class TestBrCepService(unittest.TestCase):
    @patch("custom_addons.br_base.services.br_cep_service.requests.get")
    def test_fetch_cep_valido(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "logradouro": "Praca da Se",
            "bairro": "Se",
            "localidade": "Sao Paulo",
            "uf": "SP",
            "ibge": "3550308",
        }
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        result = fetch_cep("01001-000")

        self.assertEqual(result["uf"], "SP")
        self.assertEqual(result["ibge"], "3550308")

    @patch("custom_addons.br_base.services.br_cep_service.requests.get")
    def test_fetch_cep_invalido(self, mock_get):
        response = Mock()
        response.json.return_value = {"erro": True}
        response.raise_for_status.return_value = None
        mock_get.return_value = response
        self.assertIsNone(fetch_cep("00000000"))

    @patch("custom_addons.br_base.services.br_cep_service.requests.get")
    def test_fetch_cep_timeout(self, mock_get):
        mock_get.side_effect = TimeoutError()
        self.assertIsNone(fetch_cep("01001000"))

