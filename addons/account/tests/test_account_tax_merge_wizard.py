from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountTaxMergeWizard(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_data_2 = cls.setup_other_company(name="tax_merge_company_b")
        cls.company_b = cls.company_data_2["company"]
        cls.country = cls.company_a.account_config_id.account_fiscal_country_id
        cls.company_b.account_config_id.account_fiscal_country_id = cls.country
        cls.shared_account = cls.company_data["default_account_revenue"].sudo()
        code_in_b = (
            cls.env["account.account"]
            .with_company(cls.company_b)
            ._search_new_account_code(
                cls.shared_account.with_company(cls.company_a).code
            )
        )
        cls.shared_account.write(
            {
                "company_ids": [Command.link(cls.company_b.id)],
                "code_mapping_ids": [
                    Command.create({"company_id": cls.company_b.id, "code": code_in_b})
                ],
            }
        )

    @classmethod
    def _tax(cls, company, account=None, factor=100.0):
        account = account or cls.shared_account
        return (
            cls.env["account.tax"]
            .with_company(company)
            .create(
                {
                    "name": "VAT 16%",
                    "type_tax_use": "sale",
                    "amount_type": "percent",
                    "amount": 16.0,
                    "country_id": cls.country.id,
                    "invoice_repartition_line_ids": [
                        Command.create(
                            {"document_type": "invoice", "repartition_type": "base"}
                        ),
                        Command.create(
                            {
                                "document_type": "invoice",
                                "repartition_type": "tax",
                                "factor_percent": factor,
                                "account_id": account.id,
                            }
                        ),
                    ],
                    "refund_repartition_line_ids": [
                        Command.create(
                            {"document_type": "refund", "repartition_type": "base"}
                        ),
                        Command.create(
                            {
                                "document_type": "refund",
                                "repartition_type": "tax",
                                "factor_percent": factor,
                                "account_id": account.id,
                            }
                        ),
                    ],
                }
            )
        )

    def _wizard(self, taxes):
        return (
            self.env["account.tax.merge.wizard"]
            .with_context(active_model="account.tax", active_ids=taxes.ids)
            .create({})
        )

    def _lines(self, wizard):
        return wizard.wizard_line_ids.filtered(lambda l: l.display_type == "tax")

    def test_merge_two_identical_taxes(self):
        tax_a = self._tax(self.company_a)
        tax_b = self._tax(self.company_b)
        wizard = self._wizard(tax_a + tax_b)
        self.assertFalse(
            any(self._lines(wizard).mapped("info")),
            "two identical taxes in different companies must be mergeable",
        )

        wizard.action_merge()
        survivor = (tax_a + tax_b).exists()
        self.assertEqual(len(survivor), 1, "one tax must survive the merge")
        self.assertEqual(
            survivor.company_ids,
            self.company_a + self.company_b,
            "the survivor must serve both companies",
        )
        self.assertEqual(
            len(survivor.repartition_line_ids),
            4,
            "the survivor keeps its own distribution, not both taxes' lines",
        )

    def test_a_tax_used_by_a_posted_entry_survives_the_merge(self):
        tax_a = self._tax(self.company_a)
        tax_b = self._tax(self.company_b)
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "price_unit": 100.0,
                            "tax_ids": [Command.set(tax_a.ids)],
                        }
                    )
                ],
            }
        )
        move.action_post()
        tax_line = move.line_ids.filtered("tax_repartition_line_id")
        self.assertTrue(tax_line, "control: the entry must carry a tax line")

        self._wizard(tax_a + tax_b).action_merge()

        survivor = (tax_a + tax_b).exists()
        self.assertEqual(len(survivor), 1)
        self.assertIn(
            tax_line.tax_repartition_line_id,
            survivor.repartition_line_ids,
            "the journal item must point at the surviving tax's distribution",
        )
        self.assertEqual(
            move.line_ids.tax_ids, survivor, "the tax link must survive the merge"
        )

    def test_two_taxes_of_one_company_cannot_share_a_name(self):
        self._tax(self.company_a)
        with self.assertRaises(ValidationError):
            self._tax(self.company_a)

    def test_taxes_with_different_distributions_are_refused(self):
        tax_a = self._tax(self.company_a)
        tax_b = self._tax(
            self.company_b, account=self.company_data_2["default_account_expense"]
        )
        wizard = self._wizard(tax_a + tax_b)
        self.assertTrue(
            any(self._lines(wizard).mapped("info")),
            "same rate but a different distribution account is not the same tax",
        )
        self.assertTrue(wizard.disable_merge_button)

    def test_taxes_with_a_different_distribution_shape_are_refused(self):
        tax_a = self._tax(self.company_a)
        tax_b = self._tax(self.company_b)
        (
            tax_b.invoice_repartition_line_ids + tax_b.refund_repartition_line_ids
        ).filtered(lambda line: line.repartition_type == "tax").write(
            {"factor_percent": 60.0}
        )
        tax_b.write(
            {
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "document_type": "invoice",
                            "repartition_type": "tax",
                            "factor_percent": 40.0,
                            "account_id": self.shared_account.id,
                        }
                    )
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "document_type": "refund",
                            "repartition_type": "tax",
                            "factor_percent": 40.0,
                            "account_id": self.shared_account.id,
                        }
                    )
                ],
            }
        )
        wizard = self._wizard(tax_a + tax_b)
        self.assertTrue(
            any(self._lines(wizard).mapped("info")),
            "a different distribution shape is not the same tax",
        )

    def test_unmerge_splits_a_shared_tax_back_per_company(self):
        tax_a = self._tax(self.company_a)
        tax_b = self._tax(self.company_b)
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "price_unit": 100.0,
                            "tax_ids": [Command.set(tax_a.ids)],
                        }
                    )
                ],
            }
        )
        move.action_post()
        self._wizard(tax_a + tax_b).action_merge()
        shared = (tax_a + tax_b).exists()
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared.company_ids, self.company_a + self.company_b)

        shared.with_context(account_unmerge_confirm=True).action_unmerge()

        survivors = self.env["account.tax"].search(
            [("name", "=", "VAT 16%"), ("country_id", "=", self.country.id)]
        )
        self.assertEqual(len(survivors), 2, "one tax per company after the split")
        self.assertEqual(
            survivors.company_ids,
            self.company_a + self.company_b,
            "between them the copies cover both companies again",
        )
        for tax in survivors:
            self.assertEqual(
                len(tax.company_ids), 1, "each copy serves exactly one company"
            )
            self.assertEqual(
                len(tax.repartition_line_ids), 4, "and carries its own distribution"
            )

        tax_line = move.line_ids.filtered("tax_repartition_line_id")
        self.assertIn(
            tax_line.tax_repartition_line_id,
            survivors.repartition_line_ids,
            "the journal item must follow its company's copy",
        )
        self.assertEqual(
            tax_line.tax_repartition_line_id.tax_id.company_ids,
            self.company_a,
            "and specifically onto the copy for its own company",
        )

    def test_the_generic_merge_path_is_closed(self):
        tax_a = self._tax(self.company_a)
        tax_b = self._tax(self.company_b)
        with self.assertRaises(UserError):
            tax_a._merge_method(tax_a, tax_b)
