from num2words import num2words

from odoo.tests.common import TransactionCase


class TestNum2WordsAr(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_multiple_of_thousands(self):
        """Test num2words function with a multiple of thousands number."""
        thousand = num2words(1234, lang="ar")
        million = num2words(1234567, lang="ar")
        billion = num2words(1234567890, lang="ar")

        self.assertEqual(thousand, "ألف و مئتان و أربعة و ثلاثون")
        self.assertEqual(
            million, "مليون و مئتان و أربعة و ثلاثون ألفاً و خمسمائة و سبعة و ستون")
        self.assertEqual(
            billion, "مليار و مئتان و أربعة و ثلاثون مليوناً و خمسمائة و سبعة و ستون ألفاً و ثمانمائة و تسعون")

    def test_decimal_multiple_of_thousands(self):
        """Test num2words function with a multiple of thousands number."""
        thousand = num2words(1234.1, lang="ar")
        million = num2words(1234567.23, lang="ar")
        billion = num2words(1234567890.9, lang="ar")

        self.assertEqual(thousand, "ألف و مئتان و أربعة و ثلاثون  , عشر")
        self.assertEqual(
            million, "مليون و مئتان و أربعة و ثلاثون ألفاً و خمسمائة و سبعة و ستون  , ثلاث و عشرون")
        self.assertEqual(
            billion, "مليار و مئتان و أربعة و ثلاثون مليوناً و خمسمائة و سبعة و ستون ألفاً و ثمانمائة و تسعون  , تسعون")
