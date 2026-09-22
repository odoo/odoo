from num2words import num2words

from odoo.tests.common import BaseCase, TransactionCase


class TestNum2WordsEs(BaseCase):

    def test_apocope_cardinal(self):
        for number, expected in [
            (1, "uno"),
            (21, "veintiuno"),
            (31, "treinta y uno"),
            (101, "ciento uno"),
            (1000, "mil"),
            (1001, "mil uno"),
            (21000, "veintiún mil"),
            (101000, "ciento un mil"),
            (301000, "trescientos un mil"),
            (1000000, "un millón"),
            (21000000, "veintiún millones"),
            (1000000000, "mil millones"),
            (2301439, "dos millones trescientos un mil cuatrocientos treinta y nueve"),
            (-1, "menos uno"),
            (-21000, "menos veintiún mil"),
            (-301000, "menos trescientos un mil"),
            (21000.5, "veintiún mil punto cinco"),
        ]:
            with self.subTest(number=number):
                self.assertEqual(num2words(number, lang="es"), expected)

    def test_apocope_all_spanish_variants(self):
        for lang in ("es", "es_CO", "es_VE"):
            with self.subTest(lang=lang):
                self.assertEqual(num2words(301000, lang=lang), "trescientos un mil")

    def test_unaffected_numbers(self):
        for number, expected in [
            (2, "dos"),
            (11, "once"),
            (100, "cien"),
            (1100, "mil cien"),
            (1.5, "uno punto cinco"),
            (1.21, "uno punto dos uno"),
        ]:
            with self.subTest(number=number):
                self.assertEqual(num2words(number, lang="es"), expected)

    def test_currency(self):
        for number, expected in [
            (1.01, "un euro con un céntimo"),
            (31.41, "treinta y un euros con cuarenta y un céntimos"),
            (101.01, "ciento un euros con un céntimo"),
            (2301439.88, "dos millones trescientos un mil cuatrocientos treinta y nueve euros con ochenta y ocho céntimos"),
        ]:
            with self.subTest(number=number):
                self.assertEqual(num2words(number, lang="es", to="currency", currency="EUR"), expected)

    def test_ordinal_unaffected(self):
        for number, expected in [
            (1, "primero"),
            (21, "vigésimo primero"),
            (31, "trigésimo primero"),
            (101, "centésimo primero"),
            (1001, "milésimo primero"),
            (1000000, "millonésimo"),
        ]:
            with self.subTest(number=number):
                self.assertEqual(num2words(number, lang="es", to="ordinal"), expected)


class TestNum2WordsEsAmountToText(TransactionCase):

    def test_amount_to_text(self):
        self.env['res.lang']._activate_lang('es_MX')
        currency = self.env.ref('base.MXN').with_context(lang='es_MX')

        for amount, expected in [
            (1.00, "Uno "),
            (21.00, "Veintiuno "),
            (101.00, "Ciento Uno "),
            (2301439.88, "Dos Millones Trescientos Un Mil Cuatrocientos Treinta Y Nueve "),
        ]:
            with self.subTest(amount=amount):
                self.assertIn(expected, currency.amount_to_text(amount))
