import codecs
import unittest

from odoo.libs.documents.guess import decode, guess_encoding


class TestGuessEncoding(unittest.TestCase):
    def test_utf8(self):
        self.assertEqual(guess_encoding("Café Ñoño".encode()), "utf-8")

    def test_short_utf8_is_not_left_to_the_probers(self):
        spanish = "Configuración del módulo árbol genealógico".encode()
        self.assertEqual(guess_encoding(spanish), "utf-8")
        self.assertEqual(decode(spanish), "Configuración del módulo árbol genealógico")

    def test_a_utf8_bom_is_stripped(self):
        data = codecs.BOM_UTF8 + "Café".encode()
        self.assertEqual(guess_encoding(data), "utf-8-sig")
        self.assertEqual(decode(data), "Café")

    def test_latin1_is_not_utf8(self):
        self.assertNotEqual(guess_encoding("Café".encode("latin-1")), "utf-8")

    def test_undetectable_answers_none(self):
        self.assertIsNone(guess_encoding(bytes([0x81, 0x8D, 0x8F, 0x90, 0x9D])))

    def test_bom_marked_utf16_loses_its_endianness_suffix(self):
        data = "name,total\n".encode("utf-16")
        self.assertEqual(guess_encoding(data), "utf-16")
        self.assertFalse(decode(data).startswith("﻿"))

    def test_a_codec_python_cannot_load_is_not_a_guess(self):
        from unittest import mock

        from odoo.libs.documents import guess as module

        detector = mock.Mock()
        detector.done = True
        detector.result = {"encoding": "EUC-TW"}
        with mock.patch.object(
            module.chardet, "UniversalDetector", return_value=detector
        ):
            self.assertIsNone(guess_encoding(b"whatever"))

    def test_non_ascii_past_the_first_chunk(self):
        data = b"a" * (1 << 17) + "é".encode("latin-1")
        self.assertNotIn(guess_encoding(data), (None, "ascii"))


class TestDecode(unittest.TestCase):
    def test_latin1_round_trips_without_replacement_characters(self):
        self.assertEqual(decode("Café".encode("latin-1")), "Café")

    def test_declared_encoding_is_used(self):
        self.assertEqual(decode("Café".encode("cp1252"), "cp1252"), "Café")

    def test_undetectable_raises_rather_than_substituting(self):
        with self.assertRaises(UnicodeDecodeError):
            decode(bytes([0x81, 0x8D, 0x8F, 0x90, 0x9D]))

    def test_wrong_declared_encoding_raises(self):
        with self.assertRaises(UnicodeDecodeError):
            decode("Café".encode("latin-1"), "utf-8")
