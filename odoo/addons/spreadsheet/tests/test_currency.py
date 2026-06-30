from odoo.tests.common import TransactionCase

class TestCurrencyRates(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestCurrencyRates, cls).setUpClass()
        cls.env["res.currency"].create(
            [
                {
                    "name": "MC1",
                    "symbol": ":D",
                    "rounding": 0.001,
                },
                {
                    "name": "MC2",
                    "symbol": "§",
                },
            ]
        )
        eur_company = cls.env["res.company"].create(
            {"name": "Company with EUR", "currency_id": cls.env.ref("base.EUR").id}
        )
        usd_company = cls.env["res.company"].create(
            {"name": "Company with USD", "currency_id": cls.env.ref("base.USD").id}
        )
        cls.env.user.company_ids |= eur_company
        cls.env.user.company_ids |= usd_company
        cls.env.user.company_id = eur_company
        cls.usd_company_id = usd_company.id

    def test_get_currencies_for_spreadsheet(self):
        self.assertEqual(
            self.env["res.currency"].get_currencies_for_spreadsheet(["MC1", "MC2"]),
            [
                {
                    "code": "MC1",
                    "symbol": ":D",
                    "decimalPlaces": 3,
                    "position": "after",
                },
                {
                    "code": "MC2",
                    "symbol": "§",
                    "decimalPlaces": 2,
                    "position": "after",
                },
            ],
        )

        self.assertEqual(
            self.env["res.currency"].get_currencies_for_spreadsheet(["ProbablyNotACurrencyName?", "MC2"]),
            [
                None,
                {
                    "code": "MC2",
                    "symbol": "§",
                    "decimalPlaces": 2,
                    "position": "after",
                },
            ],
        )

    def test_get_company_currency_for_spreadsheet(self):
        self.assertEqual(
            self.env["res.currency"].get_company_currency_for_spreadsheet(),
            {
                "code": "EUR",
                "symbol": "€",
                "decimalPlaces": 2,
                "position": "after",
            }
        )
        self.assertEqual(
            self.env["res.currency"].get_company_currency_for_spreadsheet(self.usd_company_id),
            {
                "code": "USD",
                "symbol": "$",
                "decimalPlaces": 2,
                "position": "before",
            }
        )
        self.assertEqual(
            self.env["res.currency"].get_company_currency_for_spreadsheet(123456),
            False
        )
