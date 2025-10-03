# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.barcode import check_barcode_encoding, get_barcode_check_digit
from odoo._monkeypatches.reportlab import datamatrix_encode_ascii

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestBarcode(TransactionCase):
    def test_barcode_check_digit(self):
        ean8 = "87111125"
        self.assertEqual(get_barcode_check_digit("0" * 10 + ean8), int(ean8[-1]))
        ean13 = "1234567891231"
        self.assertEqual(get_barcode_check_digit("0" * 5 + ean13), int(ean13[-1]))

    def test_barcode_encoding(self):
        self.assertTrue(check_barcode_encoding('20220006', 'ean8'))
        self.assertTrue(check_barcode_encoding('93855341', 'ean8'))
        self.assertTrue(check_barcode_encoding('2022071416014', 'ean13'))
        self.assertTrue(check_barcode_encoding('9745213796142', 'ean13'))

        self.assertFalse(check_barcode_encoding('2022a006', 'ean8'), 'should contains digits only')
        self.assertFalse(check_barcode_encoding('20220000', 'ean8'), 'incorrect check digit')
        self.assertFalse(check_barcode_encoding('93855341', 'ean13'), 'ean13 is a 13-digits barcode')
        self.assertFalse(check_barcode_encoding('9745213796142', 'ean8'), 'ean8 is a 8-digits barcode')
        self.assertFalse(check_barcode_encoding('9745213796148', 'ean13'), 'incorrect check digit')
        self.assertFalse(check_barcode_encoding('2022!71416014', 'ean13'), 'should contains digits only')
        self.assertFalse(check_barcode_encoding('0022071416014', 'ean13'), 'when starting with one zero, it indicates that a 12-digit UPC-A code follows')

    def _get_patched_datamatrix_components(self):
        # Helper method to get ECC200DataMatrix and skip test if not available/patched.
        try:
            from reportlab.graphics.barcode.ecc200datamatrix import ECC200DataMatrix  # noqa: PLC0415

            if not hasattr(ECC200DataMatrix,
                           '_encode_c40') or ECC200DataMatrix._encode_c40.__name__ != 'patch_encode_c40':
                _logger.warning(
                    "DataMatrix ECC200DataMatrix._encode_c40 monkeypatch was not applied correctly or found. Skipping related tests.")
                self.skipTest("DataMatrix ECC200DataMatrix._encode_c40 monkeypatch not found or not applied.")

            return ECC200DataMatrix

        except ImportError:
            _logger.warning("Reportlab ECC200DataMatrix not available, skipping DataMatrix barcode tests.")
            self.skipTest("Reportlab ECC200DataMatrix not available, skipping datamatrix barcode tests.")

    def test_datamatrix_ascii_encoding(self):
        # Call helper to ensure environment is set up and patched components are available.
        _ = self._get_patched_datamatrix_components()

        self.assertEqual(list(datamatrix_encode_ascii("2022071416014")), [150, 152, 137, 144, 146, 131, 53])
        self.assertEqual(list(datamatrix_encode_ascii("9745213796142")), [227, 175, 151, 167, 226, 144, 51])
        self.assertEqual(list(datamatrix_encode_ascii("abc123")), [98, 99, 100, 142, 52])

    def test_datamatrix_c40_encoding(self):
        patched_ecc200datamatrix = self._get_patched_datamatrix_components()

        def get_datamatrix(data):
            codewords = patched_ecc200datamatrix()._encode_c40(data)
            try:
                end_of_data_idx = codewords.index(254)
                padding_start_idx = codewords.index(129, end_of_data_idx)
                return codewords[:padding_start_idx]
            except ValueError:
                return codewords

        self.assertEqual(get_datamatrix("123a"), [230, 32, 56, 254, 52, 98])
        self.assertEqual(get_datamatrix("1234"), [230, 32, 56, 254, 53])
        self.assertEqual(get_datamatrix("1234a"), [230, 32, 56, 50, 82, 254])
        self.assertEqual(get_datamatrix("abc123"), [230, 12, 171, 12, 212, 32, 56, 254])

        self.assertEqual(get_datamatrix("2022071416014"), [230, 38, 39, 38, 44, 32, 134, 63, 38, 254, 53])
        self.assertEqual(get_datamatrix("9745213796142"), [230, 83, 1, 57, 54, 45, 134, 63, 81, 254, 51])
        self.assertEqual(
            get_datamatrix("011234567890510abcde"),
            [230, 25, 206, 38, 161, 57, 220, 77, 13, 57, 13, 12, 171, 12, 212, 13, 35, 254, 102],
        )

    def test_datamatrix_no_nul_byte_in_generated_barcode(self):
        """
        Test that Data Matrix barcode generation (via patch_encode_c40) correctly
        removes trailing (or embedded) nul bytes from input data *before* encoding.
        """
        patched_ecc200datamatrix = self._get_patched_datamatrix_components()

        data_with_nul = "Test\x00String\x00With\x00Nul"

        try:
            codewords = patched_ecc200datamatrix()._encode_c40(data_with_nul)
            self.assertGreater(len(codewords), 0, "Codewords not generated after stripping NUL bytes.")
        except Exception as e:  # noqa: BLE001
            self.fail(f"Barcode generation failed for NUL-containing input after stripping: {e}")

        data_with_trailing_nul = "TestString\x00"

        try:
            codewords_trailing = patched_ecc200datamatrix()._encode_c40(data_with_trailing_nul)
            self.assertGreater(len(codewords_trailing), 0, "Codewords not generated after stripping trailing NUL bytes.")
        except Exception as e:  # noqa: BLE001
            self.fail(f"Barcode generation failed for trailing NUL input after stripping: {e}")

    def test_datamatrix_extended_ascii_encoding(self):
        """
        Test that datamatrix_encode_ascii correctly handles Extended ASCII (ISO-8859-1) characters.
        """
        _ = self._get_patched_datamatrix_components()

        value_extended_ascii = "Héllö Wörldñ"
        self.assertEqual(list(datamatrix_encode_ascii(value_extended_ascii)),
                         [73, 235, 106, 109, 109, 235, 119, 33, 88, 235, 119, 115, 109, 101, 235, 114])

        mixed_value = "123_Á_é_789"
        self.assertEqual(list(datamatrix_encode_ascii(mixed_value)),
                         [142, 52, 96, 235, 66, 96, 235, 106, 96, 208, 58])

        value_with_nul_in_ascii = "Test\x00Extended\x00"

        try:
            result_codewords_ascii = list(datamatrix_encode_ascii(value_with_nul_in_ascii))
            self.assertGreater(len(result_codewords_ascii), 0, "Codewords not generated for NUL-containing ASCII input.")
        except Exception as e:  # noqa: BLE001
            self.fail(f"Extended ASCII encoding failed for NUL-containing input: {e}")
