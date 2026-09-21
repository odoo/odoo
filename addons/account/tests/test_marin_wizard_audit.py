from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestWizardAudit(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_journal = cls.env["account.journal"].create(
            {"name": "Audit Misc", "code": "AUDMS", "type": "general"}
        )

    def _entry(self, date):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.other_journal.id,
                "date": date,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "debit": 10.0,
                            "credit": 0.0,
                            "name": "d",
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                            "debit": 0.0,
                            "credit": 10.0,
                            "name": "c",
                        }
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def test_resequence_create_without_first_name(self):
        moves = self._entry("2026-01-05") | self._entry("2026-02-05")
        wizard = self.env["account.resequence.wizard"].create(
            {"move_ids": [Command.set(moves.ids)]}
        )
        self.assertTrue(wizard.first_name)

    def test_resequence_preview_is_computed_per_record(self):
        moves = self._entry("2026-03-05") | self._entry("2026-04-05")
        wizards = self.env["account.resequence.wizard"].create(
            [
                {"move_ids": [Command.set(moves.ids)]},
                {"move_ids": [Command.set(moves.ids)]},
            ]
        )
        self.assertEqual(len(wizards.mapped("preview_moves")), 2)

    def test_bank_setup_only_offers_journals_of_the_active_company(self):
        other = self.setup_other_company()["company"]
        self.env["account.journal"].create(
            {
                "name": "Foreign Bank",
                "code": "FRGNB",
                "type": "bank",
                "company_id": other.id,
                "bank_statements_source": "undefined",
            }
        )
        self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.env.company.id)]
        ).bank_account_id = self.env["res.partner.bank.account"].create(
            {"acc_number": "AUD-1", "partner_id": self.env.company.partner_id.id}
        )
        wizard = self.env["account.setup.bank.manual.config"]
        journal = self.env["account.journal"].browse(
            wizard.default_linked_journal_id("bank")
        )
        self.assertNotEqual(journal.company_id, other)

    def test_payment_register_totals_are_computed_once(self):
        invoices = self.env["account.move"]
        for _i in range(3):
            invoices |= self.init_invoice(
                "out_invoice", amounts=[100.0], post=True, partner=self.partner_a
            )
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoices.ids)
            .create({})
        )
        calls = []
        origin = type(wizard)._get_total_amounts_to_pay

        def counting(self, batch_results):
            calls.append(1)
            return origin(self, batch_results)

        self.patch(type(wizard), "_get_total_amounts_to_pay", counting)
        form_fields = [
            name
            for name in wizard.get_view()["models"]["account.payment.register"]
            if name in wizard._fields
        ]
        wizard.invalidate_recordset()
        wizard.read(form_fields)
        self.assertLessEqual(len(calls), 2)

        before = len(calls)
        wizard.read(form_fields)
        self.assertEqual(len(calls), before)

    def test_payment_register_does_not_redirect_to_unreadable_payments(self):
        branch_a = self._create_company(name="Audit B1", parent_id=self.env.company.id)
        branch_b = self._create_company(name="Audit B2", parent_id=self.env.company.id)
        invoices = self.env["account.move"]
        for branch in (branch_a, branch_b):
            self.env["account.journal"].create(
                {
                    "code": f"AB{branch.id}",
                    "company_id": branch.id,
                    "name": f"{branch.name} bank",
                    "type": "bank",
                }
            )
            invoices |= self.init_invoice(
                "out_invoice", products=self.product_a, company=branch
            )
        invoices.action_post()
        lines = invoices.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )

        user = self.env["res.users"].create(
            {
                "name": "Audit Branch User",
                "login": "audit_branch_user",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("account.group_account_manager").id,
                            self.env.ref("account.group_account_user").id,
                            self.env.ref("base.group_user").id,
                        ]
                    )
                ],
                "company_ids": [
                    Command.set([self.env.company.id, branch_a.id, branch_b.id])
                ],
                "company_id": branch_a.id,
            }
        )
        wizard = (
            self.env["account.payment.register"]
            .with_user(user)
            .with_context(
                allowed_company_ids=[branch_a.id, branch_b.id],
                active_model="account.move.line",
                active_ids=lines.ids,
            )
            .create({})
        )
        self.assertTrue(wizard._is_from_sibling_companies(lines))
        self.assertNotIn(lines.company_id.root_id, wizard.env.companies)
        self.assertIs(wizard.action_create_payments(), True)
