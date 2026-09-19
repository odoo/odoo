from datetime import date

from odoo import Command
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.tests import tagged

from odoo.addons.account.tests.common_reconcile import TestBankRecWidgetCommon


@tagged("post_install", "-at_install")
class TestSetAccountOnStatementLine(TestBankRecWidgetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.suspense_account = cls.bank_journal.suspense_account_id

    def _suspense_line_of(self, st_line):
        return st_line.line_ids.filtered(
            lambda line: line.account_id == self.suspense_account
        )[:1]

    def _lines_sharing_a_label(self, label, count=6):
        return self.env["account.bank.statement.line"].create(
            [
                {
                    "journal_id": self.bank_journal.id,
                    "payment_ref": "%s %04d" % (label, index),
                    "amount": -25.0,
                    "date": "2019-01-01",
                }
                for index in range(count)
            ]
        )

    def test_reserved_accounts_teach_no_rule(self):
        lines = self._lines_sharing_a_label("MONTHLY SERVICE CHARGE")
        before = self.env["account.reconcile.model"].search([])

        for st_line in lines:
            suspense_line = self._suspense_line_of(st_line)
            if suspense_line:
                st_line.set_account_bank_statement_line(
                    suspense_line.id, self.suspense_account.id
                )

        learned = self.env["account.reconcile.model"].search([]) - before
        self.assertFalse(
            learned.filtered(
                lambda model: self.suspense_account in model.line_ids.account_id
            ),
            "a rule pointing at the suspense account parks every future match as unprocessed",
        )

    def test_ordinary_account_still_teaches_a_rule(self):
        lines = self._lines_sharing_a_label("WEEKLY CLEANING FEE")
        before = self.env["account.reconcile.model"].search([])
        expense = self.company_data["default_account_expense"]

        for st_line in lines:
            suspense_line = self._suspense_line_of(st_line)
            if suspense_line:
                st_line.set_account_bank_statement_line(suspense_line.id, expense.id)

        learned = self.env["account.reconcile.model"].search([]) - before
        self.assertTrue(
            learned, "a repeated label on an ordinary account should still teach a rule"
        )

    def test_a_model_nobody_generated_survives_a_different_account(self):
        loaded_model = self._create_reconcile_model(
            name="Loaded, not learned",
            match_label="contains",
            match_label_param="ANNUAL CARD FEE",
            trigger="manual",
            line_ids=[{"account_id": self.company_data["default_account_revenue"].id}],
        )
        self.assertFalse(loaded_model.created_automatically)
        self.env.cr.execute(
            "UPDATE account_reconcile_model SET create_uid = 1 WHERE id = %s",
            (loaded_model.id,),
        )
        loaded_model.invalidate_recordset(["create_uid"])

        st_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal.id,
                "payment_ref": "ANNUAL CARD FEE",
                "amount": -25.0,
                "date": "2019-01-01",
            }
        )
        st_line._try_auto_reconcile_statement_lines()
        suspense_line = self._suspense_line_of(st_line)
        self.assertEqual(
            suspense_line.reconcile_model_id,
            loaded_model,
            "the matcher should have proposed the loaded model",
        )

        st_line.set_account_bank_statement_line(
            suspense_line.id, self.company_data["default_account_expense"].id
        )

        self.assertTrue(
            loaded_model.exists(), "a model nobody generated must not be unlinked"
        )

    def test_the_learned_fee_model_carries_no_external_id(self):
        self.env["ir.config_parameter"].set_param(
            "account.bank_rec_payment_tolerance", "0.03"
        )
        invoice_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 103.0}]
        )
        st_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal.id,
                "payment_ref": "CREDITED NET OF FEES",
                "amount": 100.0,
                "date": "2019-01-01",
            }
        )
        st_line.set_line_bank_statement_line(invoice_line.ids)
        suspense_line = self._suspense_line_of(st_line)
        self.assertTrue(suspense_line, "the fee should be left on suspense")

        st_line.set_account_bank_statement_line(
            suspense_line.id, self.company_data["default_account_expense"].id
        )

        fee_models = self.env["account.reconcile.model"].search(
            [
                ("is_bank_fee_model", "=", True),
                ("match_journal_ids", "in", self.bank_journal.ids),
            ]
        )
        self.assertTrue(fee_models, "the journal should have been given a fee model")
        self.assertEqual(
            fee_models._get_external_ids(),
            {model.id: [] for model in fee_models},
            "an external id here is a deletion order for the next module upgrade",
        )

        st_line._create_account_model_fee(
            self.company_data["default_account_expense"].id
        )
        self.assertEqual(
            self.env["account.reconcile.model"].search_count(
                [
                    ("is_bank_fee_model", "=", True),
                    ("match_journal_ids", "in", self.bank_journal.ids),
                ]
            ),
            len(fee_models),
            "a journal must never collect a second fee model",
        )

    def test_set_account_covers_every_selected_line(self):
        lines = self.env["account.bank.statement.line"].create(
            [
                {
                    "journal_id": self.bank_journal.id,
                    "payment_ref": "LOOP %s" % index,
                    "amount": 50.0,
                    "date": "2019-01-01",
                }
                for index in range(3)
            ]
        )
        receivable = self.company_data["default_account_receivable"]

        lines.set_account_bank_statement_line(
            [self._suspense_line_of(line).id for line in lines], receivable.id
        )

        for st_line in lines:
            self.assertTrue(
                st_line.line_ids.filtered(lambda line: line.account_id == receivable),
                "every selected transaction should have received the account",
            )


@tagged("post_install", "-at_install")
class TestMatchingChatterNotes(TestBankRecWidgetCommon):
    def test_unmatching_is_logged(self):
        receivable_lines = [
            self._create_invoice_line(
                "out_invoice", invoice_line_ids=[{"price_unit": 150.0}]
            )
            for _ in range(2)
        ]
        st_line = self._create_st_line(300.0, partner_id=self.partner_a.id)
        st_line.set_line_bank_statement_line(
            (receivable_lines[0] + receivable_lines[1]).ids
        )
        self.assertTrue(st_line.is_reconciled)

        removed = st_line.line_ids.filtered(
            lambda line: line.reconciled_lines_ids & receivable_lines[0]
        )
        st_line.remove_reconciled_line(removed.ids)

        bodies = st_line.move_id.message_ids.mapped("body")
        self.assertTrue(
            any("Matching unreconciled" in (body or "") for body in bodies),
            "unmatching left no trace in the chatter",
        )


@tagged("post_install", "-at_install")
class TestDeferredEntriesCompany(TestBankRecWidgetCommon):
    def test_deferral_uses_the_move_company_not_the_reader(self):
        company = self.company_data["company"]
        company.account_config_id.deferred_expense_amount_computation_method = "month"
        other = self.env["res.company"].create({"name": "Deferral Reader"})
        other.account_config_id.deferred_expense_amount_computation_method = "day"

        line = {
            "deferred_start_date": "2019-01-15",
            "deferred_end_date": "2019-03-14",
            "balance": 600.0,
            "account_id": self.company_data["default_account_expense"].id,
            "product_id": False,
            "product_category_id": False,
            "move_id": False,
        }
        period = (date(2019, 1, 1), date(2019, 1, 31), "current")

        AccountMove = self.env["account.move"]
        as_owner = AccountMove.with_company(company)._get_deferred_amounts_by_line(
            [line], [period], "expense", company=company
        )
        as_reader = AccountMove.with_company(other)._get_deferred_amounts_by_line(
            [line], [period], "expense", company=company
        )
        self.assertEqual(
            as_owner[0][period],
            as_reader[0][period],
            "the reader's active company changed the deferral amount",
        )

        by_reader_company = AccountMove._get_deferred_amounts_by_line(
            [line], [period], "expense", company=other
        )
        self.assertNotEqual(
            as_owner[0][period],
            by_reader_company[0][period],
            "the two companies must really disagree, or this test proves nothing",
        )


@tagged("post_install", "-at_install")
class TestReconcileModelRpcScope(TestBankRecWidgetCommon):
    def test_the_rpc_answers_only_for_lines_the_caller_can_read(self):
        other = self.setup_other_company(name="RPC Scope Co")
        foreign_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": other["default_journal_bank"].id,
                "payment_ref": "elsewhere",
                "amount": -10.0,
                "date": "2019-01-01",
                "company_id": other["company"].id,
            }
        )
        own_line = self._create_st_line(-10.0, payment_ref="here")

        user = self.env["res.users"].create(
            {
                "name": "Reads One Company",
                "login": "rpc_scope_probe",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.company.ids)],
                "group_ids": [
                    Command.link(self.env.ref("account.group_account_user").id)
                ],
            }
        )
        ReconcileModel = self.env(user=user)["account.reconcile.model"]

        self.assertIn(
            own_line.id,
            ReconcileModel.get_available_reconcile_model_per_statement_line(
                own_line.ids
            ),
        )
        with self.assertRaises(AccessError):
            ReconcileModel.get_available_reconcile_model_per_statement_line(
                foreign_line.ids
            )
        with self.assertRaises(AccessError):
            ReconcileModel.get_available_reconcile_model_per_statement_line(
                (own_line + foreign_line).ids
            )


@tagged("post_install", "-at_install")
class TestUnreconciledActionOpeners(TestBankRecWidgetCommon):
    def test_account_narrows_the_action_to_itself(self):
        account = self.company_data["default_account_receivable"]
        action = account.action_view_reconcile()
        self.assertIn(
            ("account_id", "=", account.id),
            list(Domain(action["domain"])),
            "the account's own leaf should be added to the action's domain",
        )
        self.assertIn(
            ("full_reconcile_id", "=", False),
            list(Domain(action["domain"])),
            "and the action's own leaves should still be there",
        )

    def test_payment_narrows_the_action_to_its_partner(self):
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": 100.0,
            }
        )
        context = payment.action_view_manual_reconciliation_widget()["context"]
        self.assertEqual(context["search_default_partner_id"], self.partner_a.id)
        self.assertEqual(context["search_default_trade_receivable"], 1)
        self.assertTrue(
            context["search_default_unreconciled"],
            "the action's own context keys must survive the narrowing",
        )

    def test_a_general_journal_opens_the_action_unchanged(self):
        journal = self.env["account.journal"].search(
            [
                ("type", "=", "general"),
                ("company_id", "=", self.company_data["company"].id),
            ],
            limit=1,
        )
        action = journal.action_view_reconcile()
        self.assertEqual(action["res_model"], "account.move.line")


@tagged("post_install", "-at_install")
class TestReconciledLineOrdering(TestBankRecWidgetCommon):
    def test_the_entries_tie_on_sequence(self):
        lines = self._three_invoice_lines()
        self.assertEqual(
            len(set(lines.mapped("sequence"))),
            1,
            "the ordering column is expected to be the same for all three",
        )

    def test_counterpart_lines_follow_a_total_order(self):
        lines = self._three_invoice_lines()
        st_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.company_data["default_journal_bank"].id,
                "payment_ref": "ORDER PROBE",
                "amount": 600.0,
                "date": "2019-01-01",
            }
        )
        st_line.set_line_bank_statement_line(lines.ids)

        reconciled = st_line.line_ids.filtered("reconciled_lines_ids")
        self.assertEqual(
            reconciled.reconciled_lines_ids.ids,
            sorted(lines.ids),
            "the counterpart lines must follow the entries in a defined order",
        )

    def _three_invoice_lines(self):
        lines = self.env["account.move.line"]
        for price_unit in (100.0, 200.0, 300.0):
            lines |= self._create_invoice_line(
                "out_invoice", invoice_line_ids=[{"price_unit": price_unit}]
            )
        return lines
