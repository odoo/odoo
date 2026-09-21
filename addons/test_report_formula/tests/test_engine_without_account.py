from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEngineWithoutAccount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.anna, cls.bruno = cls.env["res.partner"].create(
            [{"name": "Anna"}, {"name": "Bruno"}]
        )
        cls.env["test.report.formula.entry"].create(
            [
                {
                    "name": f"entry {amount}",
                    "date": date,
                    "amount": amount,
                    "partner_id": partner.id,
                }
                for partner, date, amount in (
                    (cls.anna, "2020-01-10", 100.0),
                    (cls.anna, "2020-01-20", 50.0),
                    (cls.bruno, "2020-01-15", 25.0),
                    (cls.bruno, "2019-12-31", 1000.0),
                )
            ]
        )
        cls.report = cls.env["account.report"].create(
            {
                "name": "Amounts",
                "source_model": "test.report.formula.entry",
                "source_measure_field": "amount",
                "filter_date_range": True,
                "filter_unfold_all": True,
                "column_ids": [
                    Command.create({"name": "Balance", "expression_label": "balance"})
                ],
                "line_ids": [
                    Command.create(
                        {
                            "name": "All entries",
                            "code": "ALL",
                            "groupby": "partner_id",
                            "expression_ids": [
                                Command.create(
                                    {
                                        "label": "balance",
                                        "engine": "domain",
                                        "formula": "[('name', 'like', 'entry')]",
                                        "subformula": "sum",
                                    }
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "Twice",
                            "code": "TWICE",
                            "expression_ids": [
                                Command.create(
                                    {
                                        "label": "balance",
                                        "engine": "aggregation",
                                        "formula": "ALL.balance * 2",
                                    }
                                )
                            ],
                        }
                    ),
                ],
            }
        )

    def _options(self, date_from, date_to, **extra):
        return self.report.get_options(
            {
                "selected_variant_id": self.report.id,
                "date": {
                    "date_from": date_from,
                    "date_to": date_to,
                    "mode": "range",
                    "filter": "custom",
                },
                **extra,
            }
        )

    def test_account_is_not_installed(self):
        self.assertNotIn(
            "account.move.line",
            self.env,
            "this suite proves the engine runs without the ledger: run it on a "
            "database where account is not installed",
        )

    def test_the_domain_engine_sums_the_source_model_in_the_period(self):
        options = self._options("2020-01-01", "2020-01-31")
        lines = self.report._get_lines(options)
        values = {line["name"]: line["columns"][0]["no_format"] for line in lines}
        self.assertEqual(values["All entries"], 175.0)
        self.assertEqual(values["Twice"], 350.0)

    def test_a_line_unfolds_by_a_field_of_the_source_model(self):
        options = self._options("2020-01-01", "2020-01-31", unfold_all=True)
        lines = self.report._get_lines(options)
        values = {line["name"]: line["columns"][0]["no_format"] for line in lines}
        self.assertEqual(values.get("Anna"), 150.0)
        self.assertEqual(values.get("Bruno"), 25.0)

    def test_the_period_follows_the_calendar_year_without_a_fiscal_year(self):
        options = self._options("2019-01-01", "2019-12-31")
        lines = self.report._get_lines(options)
        values = {line["name"]: line["columns"][0]["no_format"] for line in lines}
        self.assertEqual(values["All entries"], 1000.0)
        self.assertEqual(options["date"]["string"], "2019")

    def test_a_report_without_a_source_model_refuses_a_domain_expression(self):
        self.report.source_model = False
        with self.assertRaisesRegex(Exception, "no source model"):
            self.report._get_lines(self._options("2020-01-01", "2020-01-31"))
