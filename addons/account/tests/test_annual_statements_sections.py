from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAnnualStatementsSections(TransactionCase):
    def _create_localized_balance_sheet(self, name, active):
        return self.env["report.formula"].create(
            {
                "name": name,
                "root_report_id": self.env.ref("account.balance_sheet").id,
                "country_id": self.env.ref("base.be").id,
                "chart_template": "annual_statements_test",
                "availability_condition": "coa",
                "active": active,
            }
        )

    def test_an_inactive_variant_stays_a_section_when_another_variant_links(self):
        inactive = self._create_localized_balance_sheet("Full balance sheet", False)
        self.env.invalidate_all()
        active = self._create_localized_balance_sheet("Abbreviated balance sheet", True)
        self.env.invalidate_all()

        annual_statements = (
            self.env["report.formula"]
            .with_context(active_test=False)
            .search(
                [
                    (
                        "root_report_id",
                        "=",
                        self.env.ref("account.annual_statements").id,
                    ),
                    ("chart_template", "=", "annual_statements_test"),
                ]
            )
        )

        self.assertEqual(len(annual_statements), 1)
        self.assertEqual(
            annual_statements.section_report_ids
            - self.env.ref("account.profit_and_loss")
            - self.env.ref("account.trial_balance_report"),
            inactive | active,
        )
