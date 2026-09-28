from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPendapatanBranchDepartmentScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent_company = cls.env["res.company"].create({
            "name": "Pendapatan Scope Test Foundation",
        })
        cls.company_a = cls.env["res.company"].create({
            "name": "Pendapatan Scope Test Branch A",
            "parent_id": cls.parent_company.id,
        })
        cls.company_b = cls.env["res.company"].create({
            "name": "Pendapatan Scope Test Branch B",
            "parent_id": cls.parent_company.id,
        })
        cls.department_a1 = cls.env["hr.department"].create({
            "name": "Scope Department A1",
            "company_id": cls.company_a.id,
        })
        cls.department_a2 = cls.env["hr.department"].create({
            "name": "Scope Department A2",
            "company_id": cls.company_a.id,
        })
        cls.department_b = cls.env["hr.department"].create({
            "name": "Scope Department B",
            "company_id": cls.company_b.id,
        })

        cls.income_account = cls.env["sif.coa"].create({
            "code": "TEST-PEND-INCOME",
            "name": "Test Pendapatan Income",
            "account_type": "income",
        })
        cls.cash_account = cls.env["sif.coa"].create({
            "code": "TEST-PEND-CASH",
            "name": "Test Pendapatan Cash",
            "account_type": "asset",
        })
        cls.category_a = cls.env["pendapatan.category"].create({
            "name": "Category Branch A",
            "code": "TEST-A",
            "periodicity": "bulanan",
            "coa_pendapatan_id": cls.income_account.id,
            "coa_kas_id": cls.cash_account.id,
            "company_id": cls.company_a.id,
        })
        cls.category_b = cls.env["pendapatan.category"].create({
            "name": "Category Branch B",
            "code": "TEST-B",
            "periodicity": "bulanan",
            "coa_pendapatan_id": cls.income_account.id,
            "coa_kas_id": cls.cash_account.id,
            "company_id": cls.company_b.id,
        })

        cls.user_a = cls._create_user(
            "pendapatan_scope_user_a",
            cls.company_a,
            cls.department_a1,
            [cls.company_a],
        )
        cls.manager_a = cls._create_user(
            "pendapatan_scope_manager_a",
            cls.company_a,
            cls.department_a1,
            [cls.company_a],
            extra_groups=["pendapatan.group_pendapatan_manager"],
        )
        cls.finance_central = cls._create_user(
            "pendapatan_scope_finance_central",
            cls.company_a,
            cls.department_a1,
            [cls.company_a, cls.company_b],
            extra_groups=["pendapatan.group_pendapatan_finance_central"],
        )

    @classmethod
    def _create_user(cls, login, company, department, allowed_companies, extra_groups=None):
        group_ids = [cls.env.ref("base.group_user").id]
        for xmlid in extra_groups or []:
            group_ids.append(cls.env.ref(xmlid).id)
        return cls.env["res.users"].create({
            "name": login,
            "login": login,
            "company_id": company.id,
            "company_ids": [(6, 0, [item.id for item in allowed_companies])],
            "department_id": department.id,
            "group_ids": [(6, 0, group_ids)],
        })

    def _income_values(self, company, department, category, **extra):
        values = {
            "tanggal": "2026-09-01",
            "period_label": "September 2026",
            "category_id": category.id,
            "company_id": company.id,
            "department_id": department.id,
            "amount": 125000.0,
        }
        values.update(extra)
        return values

    def _create_income_as_admin(self, company, department, category):
        model = self.env["pendapatan.pendapatan"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        return model.create(self._income_values(company, department, category))

    def test_user_sees_all_departments_in_allowed_branch_only(self):
        income_a1 = self._create_income_as_admin(self.company_a, self.department_a1, self.category_a)
        income_a2 = self._create_income_as_admin(self.company_a, self.department_a2, self.category_a)
        income_b = self._create_income_as_admin(self.company_b, self.department_b, self.category_b)

        scoped_model = self.env["pendapatan.pendapatan"].with_user(self.user_a).with_context(
            allowed_company_ids=[self.company_a.id],
        )
        visible_ids = set(scoped_model.search([
            ("id", "in", [income_a1.id, income_a2.id, income_b.id]),
        ]).ids)

        self.assertEqual(visible_ids, {income_a1.id, income_a2.id})

    def test_department_and_category_must_match_branch(self):
        model = self.env["pendapatan.pendapatan"].with_user(self.user_a).with_context(
            allowed_company_ids=[self.company_a.id],
        )
        with self.assertRaises(AccessError):
            model.create(self._income_values(self.company_a, self.department_b, self.category_a))

        admin_model = self.env["pendapatan.pendapatan"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        with self.assertRaises(ValidationError):
            admin_model.create(self._income_values(self.company_a, self.department_b, self.category_a))
        with self.assertRaises(ValidationError):
            admin_model.create(self._income_values(self.company_a, self.department_a1, self.category_b))

    def test_central_finance_can_read_all_allowed_branches_but_not_write(self):
        income_a = self._create_income_as_admin(self.company_a, self.department_a1, self.category_a)
        income_b = self._create_income_as_admin(self.company_b, self.department_b, self.category_b)
        central_model = self.env["pendapatan.pendapatan"].with_user(self.finance_central).with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )

        visible_ids = set(central_model.search([
            ("id", "in", [income_a.id, income_b.id]),
        ]).ids)
        self.assertEqual(visible_ids, {income_a.id, income_b.id})

        with self.assertRaises(AccessError):
            central_model.create(self._income_values(self.company_a, self.department_a1, self.category_a))
        with self.assertRaises(AccessError):
            central_model.browse(income_a.id).write({"description": "should not be editable"})
        with self.assertRaises(AccessError):
            central_model.create_pendapatan_from_external(
                self._income_values(self.company_a, self.department_a1, self.category_a),
            )
        with self.assertRaises(AccessError):
            self.env["pendapatan.category"].with_user(self.finance_central).browse(
                self.category_a.id,
            ).write({"name": "should not be editable"})
        with self.assertRaises(AccessError):
            self.env["sif.coa"].with_user(self.finance_central).browse(
                self.income_account.id,
            ).write({"name": "should not be editable"})

    def test_posting_carries_company_and_department_to_journal(self):
        income_model = self.env["pendapatan.pendapatan"].with_user(self.user_a).with_context(
            allowed_company_ids=[self.company_a.id],
        )
        income = income_model.create(
            self._income_values(self.company_a, self.department_a1, self.category_a),
        )
        income.action_submit()
        manager_income = income.with_user(self.manager_a).with_context(
            allowed_company_ids=[self.company_a.id],
        )
        manager_income.action_approve()
        manager_income.action_post()

        self.assertEqual(manager_income.state, "posted")
        self.assertEqual(manager_income.journal_id.company_id, self.company_a)
        self.assertEqual(manager_income.journal_id.department_id, self.department_a1)
        self.assertEqual(manager_income.journal_id.unit_name, self.department_a1.name)
        self.assertEqual(manager_income.journal_id.source_type, "pendapatan")

        central_journal = manager_income.journal_id.with_user(self.finance_central).with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        with self.assertRaises(AccessError):
            central_journal.write({"ref": "Finance pusat tidak boleh mengubah jurnal"})

    def test_journal_reports_are_scoped_to_allowed_companies(self):
        journal_model = self.env["sif.jurnal.entry"].sudo().with_context(
            allowed_company_ids=[self.company_a.id, self.company_b.id],
        )
        entries = []
        for company, department, prefix in [
            (self.company_a, self.department_a1, "A"),
            (self.company_b, self.department_b, "B"),
        ]:
            entry = journal_model.create({
                "date": "2026-09-10",
                "ref": "Branch report " + prefix,
                "unit_name": department.name,
                "company_id": company.id,
                "department_id": department.id,
                "source_type": "manual",
                "line_ids": [
                    (0, 0, {
                        "account_id": self.cash_account.id,
                        "name": "Debit " + prefix,
                        "debit": 500.0,
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "account_id": self.income_account.id,
                        "name": "Credit " + prefix,
                        "debit": 0.0,
                        "credit": 500.0,
                    }),
                ],
            })
            entry.action_post()
            entries.append(entry)

        scoped_context = {"allowed_company_ids": [self.company_a.id]}
        visible_journals = self.env["sif.jurnal.entry"].with_user(self.user_a).with_context(
            **scoped_context,
        ).search([("id", "in", [entry.id for entry in entries])])
        self.assertEqual(visible_journals.ids, [entries[0].id])

        ledger = self.env["sif.general.ledger"].with_user(self.user_a).with_context(
            **scoped_context,
        ).get_general_ledger_data({
            "date_from": "2026-09-01",
            "date_to": "2026-09-30",
            "target_move": "posted",
        })
        ledger_entry_ids = {
            line["entry_id"]
            for account in ledger["accounts"]
            for line in account["lines"]
        }
        self.assertIn(entries[0].id, ledger_entry_ids)
        self.assertNotIn(entries[1].id, ledger_entry_ids)

        profit_loss = self.env["sif.profit.loss"].with_user(self.user_a).with_context(
            **scoped_context,
        ).get_profit_loss_data({
            "date_from": "2026-09-01",
            "date_to": "2026-09-30",
            "target_move": "posted",
        })
        self.assertIn(self.department_a1.name, profit_loss["units_list"])
        self.assertNotIn(self.department_b.name, profit_loss["units_list"])

        balance_sheet = self.env["sif.balance.sheet"].with_user(self.user_a).with_context(
            **scoped_context,
        ).get_balance_sheet_data({
            "date_to": "2026-09-30",
            "target_move": "posted",
        })
        self.assertIn(self.department_a1.name, balance_sheet["units_list"])
        self.assertNotIn(self.department_b.name, balance_sheet["units_list"])
