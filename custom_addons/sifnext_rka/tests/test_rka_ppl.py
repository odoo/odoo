from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("sifnext_rka", "post_install", "-at_install")
class TestRKAPPLIntegration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unit = cls.env["sifnext.unit"].create({
            "name": "Unit RKA Test",
            "code": "RKA",
            "company_id": cls.env.company.id,
        })
        cls.employee = new_test_user(
            cls.env, login="rka_employee", groups="base.group_user",
            company_id=cls.env.company.id,
        )
        cls.finance = new_test_user(
            cls.env, login="rka_finance", groups="sifnext_ppl.group_ppl_finance",
            company_id=cls.env.company.id,
        )
        cls.director = new_test_user(
            cls.env, login="rka_director", groups="sifnext_ppl.group_ppl_approver",
            company_id=cls.env.company.id,
        )
        (cls.employee | cls.finance | cls.director).write({"unit_id": cls.unit.id})
        cls.account = cls.env["account.account"].create({
            "name": "Biaya Integrasi RKA",
            "code": "RKATEST",
            "account_type": "expense",
            "company_ids": [Command.set(cls.env.company.ids)],
        })
        cls.other_account = cls.env["account.account"].create({
            "name": "Biaya Integrasi RKA Lain",
            "code": "RKATEST2",
            "account_type": "expense",
            "company_ids": [Command.set(cls.env.company.ids)],
        })
        cls.rka = cls.env["sifnext.rka"].with_user(cls.finance).create({
            "unit_id": cls.unit.id,
            "year": 2026,
            "account_id": cls.account.id,
            "budget_amount": 1_000_000,
        })
        cls.rka.with_user(cls.finance).action_approve()

    def _create_finance_ppl(self, amount=100_000, account=None, rka=None):
        return self.env["sifnext.ppl"].with_user(self.finance).create({
            "request_date": "2026-09-05",
            "title": "Pengujian integrasi RKA",
            "description": "Validasi dan realisasi anggaran",
            "line_ids": [Command.create({
                "description": "Biaya operasional",
                "quantity": 1,
                "unit_price": amount,
                "account_id": (account or self.account).id,
                "rka_id": (rka or self.rka).id,
            })],
        })

    def test_rka_scope_is_unique(self):
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env["sifnext.rka"].with_user(self.finance).create({
                "unit_id": self.unit.id,
                "year": 2026,
                "account_id": self.account.id,
                "budget_amount": 500_000,
            })

    def test_employee_cannot_classify_rka(self):
        ppl = self.env["sifnext.ppl"].with_user(self.employee).create({
            "request_date": "2026-09-05",
            "title": "Pengajuan pegawai",
            "description": "Tanpa klasifikasi",
            "line_ids": [Command.create({
                "description": "Kebutuhan pegawai",
                "quantity": 1,
                "unit_price": 10_000,
            })],
        })
        with self.assertRaises(AccessError):
            ppl.line_ids.with_user(self.employee).write({"rka_id": self.rka.id})

    def test_verify_requires_rka_and_valid_mapping(self):
        ppl = self.env["sifnext.ppl"].with_user(self.employee).create({
            "request_date": "2026-09-05",
            "title": "Klasifikasi Finance",
            "description": "RKA wajib sebelum verifikasi",
            "line_ids": [Command.create({
                "description": "Kebutuhan",
                "quantity": 1,
                "unit_price": 50_000,
            })],
        })
        ppl.with_user(self.employee).action_submit()
        ppl.line_ids.with_user(self.finance).write({"account_id": self.account.id})
        with self.assertRaises(ValidationError):
            ppl.with_user(self.finance).action_verify()

        ppl.line_ids.with_user(self.finance).write({"rka_id": self.rka.id})
        ppl.with_user(self.finance).action_verify()
        self.assertEqual(ppl.state, "verified")

        invalid = self._create_finance_ppl(account=self.other_account)
        with self.assertRaises(ValidationError):
            invalid.with_user(self.finance).action_submit()

    def test_insufficient_budget_blocks_workflow(self):
        ppl = self._create_finance_ppl(amount=1_000_001)
        with self.assertRaises(ValidationError):
            ppl.with_user(self.finance).action_submit()
        self.assertEqual(ppl.state, "draft")

    def test_paid_ppl_creates_idempotent_realization(self):
        ppl = self._create_finance_ppl(amount=125_000)
        ppl.with_user(self.finance).action_submit()
        ppl.with_user(self.director).action_approve()
        ppl.with_user(self.finance).write({
            "payment_method": "bank",
            "payment_date": "2026-09-06",
            "payment_reference": "TRX-RKA-001",
        })
        ppl.with_user(self.finance).action_pay()

        realization = self.env["sifnext.rka.realization"].search([("ppl_id", "=", ppl.id)])
        self.assertEqual(len(realization), 1)
        self.assertEqual(realization.amount, 125_000)
        self.assertEqual(realization.rka_id, self.rka)
        self.assertEqual(self.rka.realization_amount, 125_000)
        self.assertEqual(self.rka.remaining_amount, 875_000)

        ppl._notify_rka_paid(ppl._prepare_integration_payload())
        self.assertEqual(self.env["sifnext.rka.realization"].search_count([("ppl_id", "=", ppl.id)]), 1)

    def test_multiple_lines_are_aggregated_per_rka(self):
        ppl = self.env["sifnext.ppl"].with_user(self.finance).create({
            "request_date": "2026-09-05",
            "title": "Agregasi RKA",
            "description": "Dua detail pada RKA yang sama",
            "line_ids": [
                Command.create({
                    "description": "Detail satu", "quantity": 1, "unit_price": 600_000,
                    "account_id": self.account.id, "rka_id": self.rka.id,
                }),
                Command.create({
                    "description": "Detail dua", "quantity": 1, "unit_price": 500_000,
                    "account_id": self.account.id, "rka_id": self.rka.id,
                }),
            ],
        })
        with self.assertRaises(ValidationError):
            ppl.with_user(self.finance).action_submit()
