from freezegun import freeze_time

from odoo.tests.common import TransactionCase

CURRENT_USD = 1.5
CURRENT_EUR = 1
CURRENT_CAD = 1.2
USD_11 = 1.8
CAD_11 = 1.9
CAD_UTC = 1.3
CAD_AUS = 2

fake_now_utc = "2020-01-01 21:00:00"


class TestCurrencyRates(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestCurrencyRates, cls).setUpClass()
        usd = cls.env.ref("base.USD")
        eur = cls.env.ref("base.EUR")
        cad = cls.env.ref("base.CAD")
        new_company = cls.env["res.company"].create(
            {"name": "Test Currency Company", "currency_id": eur.id}
        )
        cls.env.user.company_ids |= new_company
        cls.env.user.company_id = new_company

        cls.env["res.currency.rate"].create(
            [
                {
                    "currency_id": usd.id,
                    "rate": CURRENT_USD,
                },
                {
                    "currency_id": cad.id,
                    "rate": CURRENT_CAD,
                },
                {
                    "name": "2021-11-11",
                    "currency_id": usd.id,
                    "rate": USD_11,
                },
                {
                    "name": "2021-11-11",
                    "currency_id": cad.id,
                    "rate": CAD_11,
                },
            ]
        )

    def test_currency_without_date(self):
        self.assertAlmostEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet("USD", "EUR"),
            CURRENT_EUR / CURRENT_USD,
        )
        self.assertAlmostEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet("EUR", "USD"),
            CURRENT_USD,
        )
        self.assertAlmostEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet("USD", "CAD"),
            CURRENT_CAD / CURRENT_USD,
        )

    def test_currency_with_date(self):
        self.assertAlmostEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet(
                "USD", "EUR", "2021-11-11"
            ),
            CURRENT_EUR / USD_11,
        )
        self.assertAlmostEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet(
                "EUR", "USD", "2021-11-11"
            ),
            USD_11,
        )
        self.assertAlmostEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet(
                "USD", "CAD", "2021-11-11"
            ),
            CAD_11 / USD_11,
        )

    def test_currency_invalid_args(self):
        self.assertEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet("INVALID", "EUR"),
            False,
        )
        self.assertEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet("EUR", "INVALID"),
            False,
        )
        self.assertEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet("INVALID", "USD"),
            False,
        )
        self.assertEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet("USD", "INVALID"),
            False,
        )
        self.assertEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet(False, "EUR"), False
        )
        self.assertEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet("EUR", False), False
        )

    @freeze_time(fake_now_utc)
    def test_rate_by_tz(self):
        cad = self.env.ref("base.CAD")
        self.env.user.tz = "UTC"
        self.env["res.currency.rate"].create(
            {
                "currency_id": cad.id,
                "rate": CAD_UTC,
            }
        )
        self.env.user.tz = "Australia/Sydney"
        self.env["res.currency.rate"].create(
            {
                "currency_id": cad.id,
                "rate": CAD_AUS,
            }
        )
        self.assertAlmostEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet("CAD", "EUR"),
            CURRENT_EUR / CAD_AUS,
        )
        self.assertAlmostEqual(
            self.env["res.currency.rate"]
            .with_context(tz="UTC")
            ._get_rate_for_spreadsheet("CAD", "EUR"),
            CURRENT_EUR / CAD_UTC,
        )

    def test_currency_with_company_id(self):
        usd = self.env.ref("base.USD")
        cad = self.env.ref("base.CAD")
        company_eur = self.env["res.company"].create({"currency_id": usd.id, "name": "EUR"})
        company_cad = self.env["res.company"].create({"currency_id": cad.id, "name": "GBP"})
        self.env["res.currency.rate"].create(
            [
                {
                    "currency_id": usd.id,
                    "rate": 0.5,
                    "company_id": company_eur.id,
                },
                {
                    "currency_id": usd.id,
                    "rate": 0.8,
                    "company_id": company_cad.id,
                },
            ]
        )

        self.assertAlmostEqual(
            self.env["res.currency.rate"].with_company(company_eur)._get_rate_for_spreadsheet(
                "USD", "EUR", None, None
            ),
            CURRENT_EUR / 0.5,
        )
        self.assertAlmostEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet(
                "USD", "EUR", None, company_eur.id
            ),
            CURRENT_EUR / 0.5,
        )
        self.assertAlmostEqual(
            self.env["res.currency.rate"]._get_rate_for_spreadsheet(
                "USD", "CAD", None, company_cad.id
            ),
            CURRENT_EUR / 0.8,
        )
