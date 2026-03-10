# @ 2016 Akretion - www.akretion.com.br -
#   Magno Costa <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from num2words.lang_PT_BR import Num2Word_PT_BR

from odoo.tests import SavepointCase


class Num2WordsPTBRTest(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.n2w = Num2Word_PT_BR()

    def test_01_amount_to_text(self):
        self.assertEqual(
            self.n2w.to_currency(99.99),
            "noventa e nove reais e noventa e nove centavos",
        )

    def test_02_amount_to_text(self):
        self.assertEqual(
            self.n2w.to_currency(1999.99),
            "mil, novecentos e noventa e nove reais" " e noventa e nove centavos",
        )

    def test_03_amount_to_text(self):
        self.assertEqual(
            self.n2w.to_currency(77777.0),
            "setenta e sete mil, setecentos e setenta" " e sete reais",
        )

    def test_04_amount_to_text(self):
        self.assertEqual(
            self.n2w.to_currency(1856333.0),
            "um milhão, oitocentos e cinquenta e seis mil,"
            " trezentos e trinta e três reais",
        )

    def test_05_amount_to_text(self):
        self.assertEqual(
            self.n2w.to_currency(9999999.0),
            "nove milhões, novecentos e noventa e nove mil,"
            " novecentos e noventa e nove reais",
        )

    def test_06_amount_to_text(self):
        self.assertEqual(
            self.n2w.to_currency(9999999999.0),
            "nove bilhões, novecentos e noventa e nove milhões,"
            " novecentos e noventa e nove mil, novecentos e"
            " noventa e nove reais",
        )
