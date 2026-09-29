from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRkaCompanyScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_company = cls.env["res.company"].create({
            "name": "RKA Scope Test Foundation",
        })
        cls.company_a = cls.env["res.company"].create({
            "name": "RKA Scope Test Branch A",
            "parent_id": cls.parent_company.id,
        })
        cls.company_b = cls.env["res.company"].create({
            "name": "RKA Scope Test Branch B",
            "parent_id": cls.parent_company.id,
        })
        cls.expense_account = cls.env["sif.coa"].create({
            "code": "RKA-SCOPE-EXPENSE",
            "name": "RKA Scope Expense",
            "account_type": "expense",
        })
        cls.asset_account = cls.env["sif.coa"].create({
            "code": "RKA-SCOPE-ASSET",
            "name": "RKA Scope Asset",
            "account_type": "asset",
        })
        cls.user_a = cls.env["res.users"].create({
            "name": "RKA Scope Branch A User",
            "login": "rka_scope_branch_a",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id])],
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.finance_central = cls.env["res.users"].create({
            "name": "RKA Finance Central",
            "login": "rka_scope_finance_central",
            "company_id": cls.company_a.id,
            "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
            "group_ids": [(6, 0, [cls.env.ref("sif_keuangan.group_sif_keuangan_central_readonly").id])],
        })

    def _create_budget(self, company):
        return self.env["sif.rka.budget"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        ).create({
            "account_id": self.expense_account.id,
            "tahun": "2026",
            "nilai": 10000.0,
            "company_id": company.id,
        })

    def _create_posted_expense(self, company, amount, suffix):
        entry = self.env["sif.jurnal.entry"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        ).create({
            "date": "2026-09-15",
            "ref": "RKA company scope " + suffix,
            "company_id": company.id,
            "source_type": "manual",
            "line_ids": [
                (0, 0, {
                    "account_id": self.expense_account.id,
                    "name": "Expense " + suffix,
                    "debit": amount,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "account_id": self.asset_account.id,
                    "name": "Payment " + suffix,
                    "debit": 0.0,
                    "credit": amount,
                }),
            ],
        })
        entry.action_post()
        return entry

    def test_same_account_year_can_have_separate_branch_budgets(self):
        budget_a = self._create_budget(self.company_a)
        budget_b = self._create_budget(self.company_b)
        self.assertEqual(budget_a.company_id, self.company_a)
        self.assertEqual(budget_b.company_id, self.company_b)

        with self.assertRaises(ValidationError):
            self._create_budget(self.company_a)

    def test_budget_search_and_realization_are_company_scoped(self):
        budget_a = self._create_budget(self.company_a)
        budget_b = self._create_budget(self.company_b)
        self._create_posted_expense(self.company_a, 1200.0, "A")
        self._create_posted_expense(self.company_b, 3400.0, "B")

        self.assertEqual(budget_a.realisasi, 1200.0)
        self.assertEqual(budget_b.realisasi, 3400.0)

        visible = self.env["sif.rka.budget"].with_user(self.user_a).with_context(
            allowed_company_ids=[self.company_a.id],
        ).search([("id", "in", [budget_a.id, budget_b.id])])
        self.assertEqual(visible.ids, [budget_a.id])

        central = self.env["sif.rka.budget"].with_user(self.finance_central).with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        self.assertEqual(
            set(central.search([("id", "in", [budget_a.id, budget_b.id])]).ids),
            {budget_a.id, budget_b.id},
        )
        with self.assertRaises(AccessError):
            central.browse(budget_a.id).write({"nilai": 1.0})
