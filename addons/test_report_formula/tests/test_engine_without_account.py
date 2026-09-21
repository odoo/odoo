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

    def test_the_client_entry_point_serves_lines_and_the_generic_carets(self):
        options = self._options("2020-01-01", "2020-01-31")
        information = self.report.dispatch_report_action(
            options, "get_report_information"
        )
        self.assertEqual(
            [line["name"] for line in information["lines"]],
            ["All entries", "Anna", "Bruno", "Twice"],
        )
        self.assertEqual(list(information["caret_options"]), ["res.partner"])
        self.assertEqual(information["annotations"], {})

    def test_auditing_a_cell_opens_the_source_model(self):
        options = self._options("2020-01-01", "2020-01-31")
        line = self.report.line_ids.filtered(lambda line: line.code == "ALL")
        action = self.report.action_audit_cell(
            options,
            {
                "report_line_id": line.id,
                "expression_label": "balance",
                "column_group_key": next(iter(options["column_groups"])),
                "calling_line_dict_id": self.report._get_generic_line_id(
                    "account.report.line", line.id
                ),
            },
        )
        self.assertEqual(action["res_model"], "test.report.formula.entry")
        audited = self.env["test.report.formula.entry"].search(action["domain"])
        self.assertEqual(sorted(audited.mapped("amount")), [25.0, 50.0, 100.0])

    def test_a_manual_value_is_stored_and_the_aggregations_follow(self):
        manual_line = self.env["account.report.line"].create(
            {
                "name": "Manual",
                "code": "MAN",
                "report_id": self.report.id,
                "expression_ids": [
                    Command.create(
                        {
                            "label": "balance",
                            "engine": "external",
                            "formula": "sum",
                            "subformula": "editable",
                        }
                    )
                ],
            }
        )
        self.report.line_ids.filtered(
            lambda line: line.code == "TWICE"
        ).expression_ids.formula = "ALL.balance * 2 + MAN.balance"
        options = self._options("2020-01-01", "2020-01-31")
        information = self.report.get_report_information(options)
        result = self.report.action_modify_manual_value(
            self.report._get_generic_line_id("account.report.line", manual_line.id),
            options,
            next(iter(options["column_groups"])),
            "7",
            manual_line.expression_ids.id,
            2,
            information["column_groups_totals"],
        )
        values = {
            line["name"]: line["columns"][0]["no_format"] for line in result["lines"]
        }
        self.assertEqual(values["Manual"], 7.0)
        self.assertEqual(values["Twice"], 357.0)
        self.assertEqual(
            self.env["account.report.external.value"]
            .search(
                [("target_report_expression_id", "=", manual_line.expression_ids.id)]
            )
            .mapped("value"),
            [7.0],
        )

    def test_the_report_exports_to_xlsx(self):
        options = self._options("2020-01-01", "2020-01-31")
        export = self.report.dispatch_report_action(options, "export_to_xlsx")
        self.assertEqual(export["file_type"], "xlsx")
        self.assertTrue(export["file_content"].startswith(b"PK"))

    def test_the_report_renders_its_pdf_body(self):
        options = self._options("2020-01-01", "2020-01-31", export_mode="print")
        html = str(
            self.report._get_pdf_export_html(options, self.report._get_lines(options))
        )
        self.assertIn("All entries", html)
        self.assertIn("175.00", html)
        self.assertIn("report_formula.assets_pdf_export", html)
