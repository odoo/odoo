import unittest

from custom_addons.br_sped.utils.br_sped_writer import BrSpedWriter


class TestBrSpedWriter(unittest.TestCase):
    def test_writer_formata_linha_corretamente(self):
        writer = BrSpedWriter(company=None, period_from="2025-01-01", period_to="2025-01-31")
        self.assertEqual(writer.write_line("0000", ["A", "B"]), "|0000|A|B|\n")

    def test_hash_md5_calculado(self):
        writer = BrSpedWriter(company=None, period_from="2025-01-01", period_to="2025-01-31")
        self.assertEqual(len(writer.get_hash_md5(b"abc")), 32)
