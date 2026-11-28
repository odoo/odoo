import base64
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("sifnext_ppl", "post_install", "-at_install")
class TestPPLWorkflow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unit = cls.env["sifnext.unit"].create({
            "name": "Unit Automated Test PPL",
            "code": "AUTOTEST",
            "company_id": cls.env.company.id,
        })
        cls.user = new_test_user(
            cls.env,
            login="test_ppl_user",
            groups="base.group_user",
            company_id=cls.env.company.id,
        )
        cls.other_user = new_test_user(
            cls.env,
            login="test_ppl_other",
            groups="base.group_user",
            company_id=cls.env.company.id,
        )
        cls.finance = new_test_user(
            cls.env,
            login="test_ppl_finance",
            groups="sifnext_ppl.group_ppl_finance",
            company_id=cls.env.company.id,
        )
        cls.director = new_test_user(
            cls.env,
            login="test_ppl_director",
            groups="sifnext_ppl.group_ppl_approver",
            company_id=cls.env.company.id,
        )
        (cls.user | cls.other_user | cls.finance | cls.director).write({"unit_id": cls.unit.id})
        cls.account = cls.env["account.account"].create({
            "name": "Biaya PPL Test",
            "code": "PPLTEST",
            "account_type": "expense",
            "company_ids": [Command.set(cls.env.company.ids)],
        })
        cls.journal_account_parent = cls.env["sif.coa"].create({
            "name": "Beban Test PPL",
            "code": "PPL-JOURNAL-PARENT",
            "account_type": "expense",
        })
        cls.journal_account = cls.env["sif.coa"].create({
            "name": "Biaya Operasional Test PPL",
            "code": "PPL-JOURNAL-LINE",
            "account_type": "expense",
            "parent_id": cls.journal_account_parent.id,
        })
        cls.payment_account_parent = cls.env["sif.coa"].create({
            "name": "Sumber Dana Test PPL",
            "code": "PPL-PAYMENT-PARENT",
            "account_type": "asset",
        })
        cls.kas_account = cls.env["sif.coa"].create({
            "name": "Kas Besar Test PPL",
            "code": "PPL-PAYMENT-KAS",
            "account_type": "asset",
            "parent_id": cls.payment_account_parent.id,
        })
        cls.bank_account = cls.env["sif.coa"].create({
            "name": "Bank Operasional Test PPL",
            "code": "PPL-PAYMENT-BANK",
            "account_type": "asset",
            "parent_id": cls.payment_account_parent.id,
        })

    def _create_ppl(self):
        return self.env["sifnext.ppl"].with_user(self.user).create({
            "title": "Pengadaan alat tulis",
            "description": "Kebutuhan operasional",
            "line_ids": [Command.create({
                "description": "Alat tulis",
                "quantity": 2,
                "unit_price": 50_000,
            })],
        })

    def test_id_and_number_are_automatic_and_immutable(self):
        ppl = self.env["sifnext.ppl"].with_user(self.user).create({
            "name": "NOMOR-DARI-KLIEN",
            "request_date": "2026-09-05",
            "title": "Uji nomor otomatis",
            "description": "Nomor wajib berasal dari sequence",
        })

        self.assertIsInstance(ppl.id, int)
        self.assertGreater(ppl.id, 0)
        self.assertRegex(ppl.name, r"^AUTOTEST/PPL/09/2026/\d{5}$")
        self.assertNotEqual(ppl.name, "NOMOR-DARI-KLIEN")
        with self.assertRaises(UserError):
            ppl.with_user(self.user).write({"name": "AUTOTEST/PPL/09/2026/99999"})

    def test_copy_gets_a_new_number_and_keeps_unit(self):
        ppl = self._create_ppl()
        duplicate = ppl.with_user(self.user).copy()

        self.assertEqual(duplicate.unit_id, self.unit)
        self.assertNotEqual(duplicate.name, ppl.name)
        self.assertRegex(duplicate.name, r"^AUTOTEST/PPL/\d{2}/\d{4}/\d{5}$")

    def test_uat_accounts_are_provisioned_with_expected_roles(self):
        employee = self.env.ref("sifnext_ppl.user_ppl_uat_employee")
        finance = self.env.ref("sifnext_ppl.user_ppl_uat_finance")
        director = self.env.ref("sifnext_ppl.user_ppl_uat_director")
        uat_unit = self.env.ref("sifnext_ppl.unit_uat_ppl")

        self.assertEqual(employee.login, "ppl_user")
        self.assertEqual(finance.login, "ppl_finance")
        self.assertEqual(director.login, "ppl_director")
        self.assertEqual(employee.unit_id, uat_unit)
        self.assertEqual(finance.unit_id, uat_unit)
        self.assertEqual(director.unit_id, uat_unit)
        self.assertTrue(employee.has_group("base.group_user"))
        self.assertFalse(employee.has_group("sifnext_ppl.group_ppl_finance"))
        self.assertFalse(employee.has_group("sifnext_ppl.group_ppl_approver"))
        self.assertTrue(finance.has_group("sifnext_ppl.group_ppl_finance"))
        self.assertFalse(finance.has_group("sifnext_ppl.group_ppl_approver"))
        self.assertTrue(director.has_group("sifnext_ppl.group_ppl_approver"))
        self.assertFalse(director.has_group("sifnext_ppl.group_ppl_finance"))

    def test_unit_code_is_normalized_and_unique_per_company(self):
        self.assertEqual(self.unit.code, "AUTOTEST")
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env["sifnext.unit"].create({
                "name": "Duplikat Automated Test",
                "code": " autotest ",
                "company_id": self.env.company.id,
            })

    def test_number_keeps_original_value_when_draft_date_changes(self):
        ppl = self.env["sifnext.ppl"].with_user(self.user).create({
            "request_date": "2026-09-05",
            "title": "Uji perubahan tanggal",
            "description": "Nomor tidak diterbitkan ulang",
        })
        original_number = ppl.name

        ppl.with_user(self.user).write({"request_date": "2027-01-10"})

        self.assertEqual(ppl.name, original_number)
        self.assertEqual(str(ppl.request_date), "2027-01-10")

    def test_new_ppl_requires_applicant_unit(self):
        self.user.write({"unit_id": False})
        with self.assertRaises(ValidationError):
            self.env["sifnext.ppl"].with_user(self.user).create({
                "title": "Tanpa Unit",
                "description": "Harus ditolak",
            })
        self.user.write({"unit_id": self.unit.id})

    def test_employee_submit_without_coa_then_finance_verify(self):
        ppl = self._create_ppl()
        self.assertEqual(ppl.applicant_id, self.user)
        self.assertEqual(ppl.unit_id, self.unit)
        self.assertEqual(ppl.source_type, "manual")
        self.assertEqual(ppl.total_amount, 100_000)
        self.assertNotEqual(ppl.name, "New")

        ppl.with_user(self.user).action_submit()
        self.assertEqual(ppl.state, "submitted")

        with self.assertRaises(AccessError):
            ppl.line_ids.with_user(self.user).write({"journal_account_id": self.journal_account.id})
        with self.assertRaises(ValidationError):
            ppl.with_user(self.finance).action_verify()

        ppl.line_ids.with_user(self.finance).write({"journal_account_id": self.journal_account.id})
        ppl.with_user(self.finance).action_verify()
        self.assertEqual(ppl.state, "verified")
        self.assertEqual(ppl.verified_by, self.finance)

    def test_finance_can_select_master_coa_and_payload_exposes_it(self):
        ppl = self._create_ppl()
        ppl.with_user(self.user).action_submit()

        with self.assertRaises(AccessError):
            ppl.line_ids.with_user(self.user).write({
                "journal_account_id": self.journal_account.id,
            })

        ppl.line_ids.with_user(self.finance).write({
            "journal_account_id": self.journal_account.id,
        })
        payload = ppl._prepare_integration_payload()

        self.assertEqual(ppl.line_ids.journal_account_id, self.journal_account)
        self.assertEqual(
            payload["ppl"]["lines"][0]["account"],
            {
                "id": self.journal_account.id,
                "code": self.journal_account.code,
                "name": self.journal_account.name,
            },
        )

    def test_finance_submission_skips_own_verification(self):
        ppl = self.env["sifnext.ppl"].with_user(self.finance).create({
            "title": "Pengajuan Keuangan",
            "description": "Langsung menunggu Direktur",
            "line_ids": [Command.create({
                "description": "Biaya operasional",
                "quantity": 1,
                "unit_price": 75_000,
                "journal_account_id": self.journal_account.id,
            })],
        })
        ppl.with_user(self.finance).action_submit()
        self.assertEqual(ppl.state, "verified")
        self.assertEqual(ppl.submitted_by, self.finance)
        self.assertEqual(ppl.verified_by, self.finance)
        self.assertTrue(ppl.submitted_at)
        self.assertEqual(ppl.verified_at, ppl.submitted_at)

    def test_finance_submission_requires_coa(self):
        ppl = self.env["sifnext.ppl"].with_user(self.finance).create({
            "title": "Pengajuan Keuangan tanpa COA",
            "description": "Harus ditolak",
            "line_ids": [Command.create({
                "description": "Biaya operasional",
                "quantity": 1,
                "unit_price": 75_000,
            })],
        })
        with self.assertRaises(ValidationError):
            ppl.with_user(self.finance).action_submit()
        self.assertEqual(ppl.state, "draft")

    def test_item_supports_multiple_attachments_and_locks_them_after_submit(self):
        ppl = self._create_ppl()
        line = ppl.line_ids
        attachments = self.env["ir.attachment"].with_user(self.user).create([
            {
                "name": "invoice.pdf",
                "datas": base64.b64encode(b"invoice"),
                "mimetype": "application/pdf",
                "res_model": "sifnext.ppl.line",
                "res_id": line.id,
            },
            {
                "name": "receipt.jpg",
                "datas": base64.b64encode(b"receipt"),
                "mimetype": "image/jpeg",
                "res_model": "sifnext.ppl.line",
                "res_id": line.id,
            },
        ])
        line.with_user(self.user).write({"attachment_ids": [Command.set(attachments.ids)]})

        self.assertEqual(line.attachment_count, 2)
        self.assertEqual(set(line.attachment_ids.mapped("name")), {"invoice.pdf", "receipt.jpg"})
        ppl.with_user(self.user).action_submit()

        with self.assertRaises(UserError):
            line.with_user(self.user).write({"attachment_ids": [Command.clear()]})
        with self.assertRaises(UserError):
            attachments[0].with_user(self.user).write({"name": "changed.pdf"})
        with self.assertRaises(UserError):
            attachments[0].with_user(self.user).unlink()
        with self.assertRaises(UserError):
            self.env["ir.attachment"].with_user(self.user).create({
                "name": "late.pdf",
                "datas": base64.b64encode(b"late"),
                "res_model": "sifnext.ppl.line",
                "res_id": line.id,
            })

    def test_copy_does_not_reuse_item_attachments(self):
        ppl = self._create_ppl()
        attachment = self.env["ir.attachment"].with_user(self.user).create({
            "name": "private-proof.pdf",
            "datas": base64.b64encode(b"proof"),
            "res_model": "sifnext.ppl.line",
            "res_id": ppl.line_ids.id,
        })
        ppl.line_ids.with_user(self.user).write({
            "attachment_ids": [Command.link(attachment.id)],
        })

        duplicate = ppl.with_user(self.user).copy()

        self.assertFalse(duplicate.line_ids.attachment_ids)
        self.assertEqual(ppl.line_ids.attachment_ids, attachment)

    def test_submitted_request_content_is_locked(self):
        ppl = self._create_ppl()
        ppl.with_user(self.user).action_submit()
        with self.assertRaises(UserError):
            ppl.with_user(self.user).write({"title": "Diubah"})
        with self.assertRaises(UserError):
            ppl.line_ids.with_user(self.finance).write({"unit_price": 1})
        with self.assertRaises(UserError):
            ppl.with_user(self.finance).write({
                "line_ids": [Command.update(ppl.line_ids.id, {"unit_price": 1})],
            })
        with self.assertRaises(UserError):
            ppl.with_user(self.finance).write({
                "line_ids": [Command.create({
                    "description": "Baris tambahan",
                    "quantity": 1,
                    "unit_price": 10_000,
                })],
            })
        with self.assertRaises(UserError):
            ppl.with_user(self.finance).write({
                "line_ids": [Command.delete(ppl.line_ids.id)],
            })

    def test_finance_can_set_submitted_coa_through_parent_form_payload(self):
        ppl = self._create_ppl()
        ppl.with_user(self.user).action_submit()

        ppl.with_user(self.finance).write({
            "request_date": ppl.request_date,
            "applicant_id": ppl.applicant_id.id,
            "unit_id": ppl.unit_id.id,
            "partner_id": ppl.partner_id.id or False,
            "title": ppl.title,
            "description": ppl.description,
            "source_type": ppl.source_type,
            "line_ids": [Command.update(ppl.line_ids.id, {"journal_account_id": self.journal_account.id})],
        })

        self.assertEqual(ppl.line_ids.journal_account_id, self.journal_account)
        ppl.with_user(self.finance).action_verify()
        self.assertEqual(ppl.state, "verified")

    def test_employee_cannot_impersonate_applicant(self):
        with self.assertRaises(AccessError):
            self.env["sifnext.ppl"].with_user(self.user).create({
                "applicant_id": self.other_user.id,
                "title": "Tidak valid",
                "description": "Tidak valid",
            })

    def test_employee_only_sees_own_requests(self):
        own_ppl = self._create_ppl()
        other_ppl = self.env["sifnext.ppl"].with_user(self.other_user).create({
            "title": "PPL user lain",
            "description": "Tidak boleh terlihat",
            "line_ids": [Command.create({
                "description": "Item",
                "quantity": 1,
                "unit_price": 10_000,
            })],
        })
        user_results = self.env["sifnext.ppl"].with_user(self.user).search([
            ("id", "in", (own_ppl | other_ppl).ids),
        ])
        finance_results = self.env["sifnext.ppl"].with_user(self.finance).search([
            ("id", "in", (own_ppl | other_ppl).ids),
        ])
        self.assertEqual(user_results, own_ppl)
        self.assertEqual(finance_results, own_ppl | other_ppl)

    def test_approval_payment_and_done_without_account_move(self):
        ppl = self._create_ppl()
        ppl.with_user(self.user).action_submit()
        ppl.line_ids.with_user(self.finance).write({"journal_account_id": self.journal_account.id})
        ppl.with_user(self.finance).action_verify()

        with self.assertRaises(AccessError):
            ppl.with_user(self.finance).action_approve()
        with self.assertRaises(AccessError):
            ppl.with_user(self.user).action_approve()
        with self.assertRaises(AccessError):
            ppl.with_user(self.user).write({"state": "done"})

        move_count = self.env["account.move"].search_count([])
        ppl.with_user(self.director).action_approve()
        self.assertEqual(ppl.state, "approved")
        self.assertEqual(ppl.approved_by, self.director)
        self.assertEqual(self.env["account.move"].search_count([]), move_count)

        with self.assertRaises(AccessError):
            ppl.with_user(self.director).action_pay()
        with self.assertRaises(ValidationError):
            ppl.with_user(self.finance).action_pay()
        ppl.with_user(self.finance).write({
            "payment_method": "bank",
            "payment_source_account_id": self.bank_account.id,
            "payment_date": "2026-09-05",
            "payment_reference": "TRX-PPL-001",
        })
        ppl.with_user(self.finance).action_pay()
        self.assertEqual(ppl.state, "paid")
        self.assertEqual(ppl.paid_by, self.finance)
        self.assertEqual(self.env["account.move"].search_count([]), move_count)

        ppl.with_user(self.finance).action_done()
        self.assertEqual(ppl.state, "done")
        self.assertEqual(ppl.done_by, self.finance)
        with self.assertRaises(UserError):
            ppl.with_user(self.finance).action_done()

    def _prepare_approved_ppl(self):
        ppl = self._create_ppl()
        ppl.with_user(self.user).action_submit()
        ppl.line_ids.with_user(self.finance).write({"journal_account_id": self.journal_account.id})
        ppl.with_user(self.finance).action_verify()
        ppl.with_user(self.director).action_approve()
        ppl.with_user(self.finance).write({
            "payment_method": "bank",
            "payment_source_account_id": self.bank_account.id,
            "payment_date": "2026-09-05",
            "payment_reference": "TRX-PPL-CONTRACT",
        })
        return ppl

    def test_paid_event_contract_and_dispatch_order(self):
        ppl = self._prepare_approved_ppl()
        calls = []

        def notify_rka(record, payload):
            calls.append(("rka", record.state, payload))
            return True

        def notify_general_ledger(record, payload):
            calls.append(("general_ledger", record.state, payload))
            return True

        model_class = type(ppl)
        with patch.object(model_class, "_notify_rka_paid", notify_rka), \
             patch.object(model_class, "_notify_general_ledger_paid", notify_general_ledger):
            ppl.with_user(self.finance).action_pay()

        self.assertEqual([call[0] for call in calls], ["rka", "general_ledger"])
        self.assertEqual([call[1] for call in calls], ["paid", "paid"])
        self.assertIs(calls[0][2], calls[1][2])
        payload = calls[0][2]
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["event"], "ppl.paid")
        self.assertEqual(payload["idempotency_key"], f"ppl.paid:{ppl.company_id.id}:{ppl.id}")
        self.assertEqual(payload["ppl"]["number"], ppl.name)
        self.assertEqual(payload["ppl"]["state"], "paid")
        self.assertEqual(payload["ppl"]["total_amount"], 100_000)
        self.assertEqual(payload["ppl"]["payment"]["reference"], "TRX-PPL-CONTRACT")
        self.assertEqual(payload["ppl"]["payment"]["source_account"]["id"], self.bank_account.id)
        self.assertEqual(payload["ppl"]["payment"]["source_account"]["code"], self.bank_account.code)
        self.assertEqual(payload["ppl"]["lines"][0]["account"]["code"], self.journal_account.code)
        self.assertNotIn("attachments", payload["ppl"]["lines"][0])
        with self.assertRaises(UserError):
            ppl.with_user(self.finance).action_pay()
        self.assertEqual(len(calls), 2)

    def test_downstream_failure_rolls_back_payment(self):
        ppl = self._prepare_approved_ppl()

        def fail_general_ledger(record, payload):
            raise ValidationError("Jurnal Besar tidak tersedia")

        exception_message = "Jurnal Besar tidak tersedia"
        with self.assertRaisesRegex(ValidationError, exception_message), self.cr.savepoint():
            with patch.object(type(ppl), "_notify_general_ledger_paid", fail_general_ledger):
                ppl.with_user(self.finance).action_pay()

        ppl.invalidate_recordset()
        self.assertEqual(ppl.state, "approved")
        self.assertFalse(ppl.paid_by)
        self.assertFalse(ppl.paid_at)

    def test_budget_check_uses_versioned_payload(self):
        ppl = self._create_ppl()
        ppl.with_user(self.user).action_submit()
        ppl.line_ids.with_user(self.finance).write({"journal_account_id": self.journal_account.id})
        payloads = []

        def validate_budget(record, payload):
            payloads.append(payload)
            return True

        with patch.object(type(ppl), "_validate_rka_budget", validate_budget):
            ppl.with_user(self.finance).action_verify()

        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["schema_version"], 1)
        self.assertEqual(payloads[0]["ppl_id"], ppl.id)
        self.assertNotIn("account_id", payloads[0]["lines"][0])
        self.assertEqual(payloads[0]["lines"][0]["amount"], 100_000)

    def test_payment_data_is_restricted(self):
        ppl = self._create_ppl()
        with self.assertRaises(AccessError):
            ppl.with_user(self.user).write({"payment_reference": "INVALID"})
        with self.assertRaises(UserError):
            ppl.with_user(self.finance).write({"payment_reference": "TOO-EARLY"})
        with self.assertRaises(AccessError):
            ppl.with_user(self.user).write({"payment_source_account_id": self.bank_account.id})
        with self.assertRaises(UserError):
            ppl.with_user(self.finance).write({"payment_source_account_id": self.bank_account.id})

    def test_pay_requires_source_account(self):
        ppl = self._prepare_approved_ppl()
        ppl.with_user(self.finance).write({"payment_source_account_id": False})
        with self.assertRaises(ValidationError):
            ppl.with_user(self.finance).action_pay()
        ppl.with_user(self.finance).write({"payment_source_account_id": self.kas_account.id})
        ppl.with_user(self.finance).action_pay()
        self.assertEqual(ppl.state, "paid")
        self.assertEqual(ppl.payment_source_account_id, self.kas_account)

    def test_paid_journal_credit_follows_selected_source_account(self):
        ppl = self._prepare_approved_ppl()
        ppl.unit_id.sudo().journal_unit_dept = "sma"
        captured = []

        def create_from_ppl(record, data):
            captured.append(data)
            return True

        with patch.object(type(self.env["sif.jurnal.entry"]), "create_journal_from_ppl", create_from_ppl):
            ppl.with_user(self.finance).action_pay()

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["unit_dept"], "sma")
        credit_lines = [line for line in captured[0]["lines"] if line["credit"]]
        debit_lines = [line for line in captured[0]["lines"] if line["debit"]]
        self.assertEqual(len(credit_lines), 1)
        self.assertEqual(credit_lines[0]["account_id"], self.bank_account.id)
        self.assertEqual(credit_lines[0]["credit"], 100_000)
        self.assertEqual(debit_lines[0]["account_id"], self.journal_account.id)
        self.assertEqual(debit_lines[0]["debit"], 100_000)

    def test_return_requires_reason(self):
        ppl = self._create_ppl()
        ppl.with_user(self.user).action_submit()
        with self.assertRaises(ValidationError):
            ppl.with_user(self.finance).action_return_to_draft()
        ppl.with_user(self.finance).with_context(return_reason="Nominal perlu diperbaiki").action_return_to_draft()
        self.assertEqual(ppl.state, "draft")
        self.assertEqual(ppl.return_reason, "Nominal perlu diperbaiki")
