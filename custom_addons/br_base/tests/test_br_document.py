import unittest

from custom_addons.br_base.utils.br_document import (
    format_cnpj,
    format_cpf,
    strip_document,
    validate_cnpj,
    validate_cpf,
)


class TestBrDocument(unittest.TestCase):
    def test_cnpj_valido(self):
        validos = [
            "11.444.777/0001-61",
            "45.723.174/0001-10",
            "71.506.168/0001-11",
            "23.871.936/0001-90",
            "61.198.164/0001-60",
        ]
        self.assertTrue(all(validate_cnpj(item) for item in validos))

    def test_cnpj_invalido(self):
        invalidos = ["11.444.777/0001-62", "00.000.000/0000-00"]
        self.assertFalse(any(validate_cnpj(item) for item in invalidos))

    def test_cpf_valido(self):
        validos = [
            "529.982.247-25",
            "168.995.350-09",
            "111.444.777-35",
            "935.411.347-80",
            "123.456.789-09",
        ]
        self.assertTrue(all(validate_cpf(item) for item in validos))

    def test_cpf_invalido(self):
        invalidos = ["529.982.247-26", "111.111.111-11"]
        self.assertFalse(any(validate_cpf(item) for item in invalidos))

    def test_formatacao_cnpj(self):
        self.assertEqual(format_cnpj("11444777000161"), "11.444.777/0001-61")

    def test_formatacao_cpf(self):
        self.assertEqual(format_cpf("52998224725"), "529.982.247-25")

    def test_strip_mascara(self):
        self.assertEqual(strip_document("11.444.777/0001-61"), "11444777000161")

