import ast
from collections import defaultdict
from datetime import date

from lxml import etree

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.account.models.account_config import SOFT_LOCK_DATE_FIELDS
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestChangeLockDateWizardShape(TransactionCase):
    def test_every_soft_lock_date_has_its_four_fields(self):
        wizard_fields = self.env["account.change.lock.date"]._fields
        missing = [
            name
            for lock_date_field in SOFT_LOCK_DATE_FIELDS
            for name in (
                f"{lock_date_field}_for_me",
                f"{lock_date_field}_for_everyone",
                f"min_{lock_date_field}_exception_for_me_id",
                f"min_{lock_date_field}_exception_for_everyone_id",
            )
            if name not in wizard_fields
        ]
        self.assertFalse(missing, "lock date families declared only in part")

    def test_every_soft_lock_date_can_be_revoked(self):
        wizard = self.env["account.change.lock.date"].create({})
        for lock_date_field in SOFT_LOCK_DATE_FIELDS:
            for scope in ("me", "everyone"):
                action = wizard.with_context(
                    lock_date_field=lock_date_field, exception_scope=scope
                ).action_revoke_min_exception()
                self.assertTrue(
                    action, "%s/%s was not dispatched" % (lock_date_field, scope)
                )

        with self.assertRaises(UserError):
            wizard.with_context(
                lock_date_field="hard_lock_date", exception_scope="me"
            ).action_revoke_min_exception()
        with self.assertRaises(UserError):
            wizard.with_context(
                lock_date_field="tax_lock_date", exception_scope="nobody"
            ).action_revoke_min_exception()

    def test_the_view_only_asks_for_families_the_dispatch_accepts(self):
        arch = etree.fromstring(
            self.env.ref("account.view_account_change_lock_date").arch_db
        )
        asked = {
            ast.literal_eval(node.get("context"))["lock_date_field"]
            for node in arch.xpath("//*[@name='action_revoke_min_exception']")
        }
        self.assertEqual(
            asked,
            set(SOFT_LOCK_DATE_FIELDS),
            "the view asks to revoke a lock date family the dispatch does not accept",
        )

    def test_draft_entries_warning_covers_every_lock_date_it_depends_on(self):
        for lock_date_field in ("fiscalyear_lock_date", *SOFT_LOCK_DATE_FIELDS):
            wizard = self.env["account.change.lock.date"].create(
                {lock_date_field: "2019-06-30"}
            )
            domain = wizard._get_domain_draft_moves_in_locked_period()
            self.assertIn(
                "2019",
                repr(domain),
                "%s is recomputed for but never reaches the domain" % lock_date_field,
            )

    def test_the_wizard_locks_the_company_it_names(self):
        other = self.env["res.company"].create({"name": "Elsewhere Ltd"})
        other.sudo().account_config_id.fiscalyear_lock_date = False
        self.env.company.sudo().account_config_id.fiscalyear_lock_date = False

        wizard = (
            self.env["account.change.lock.date"]
            .with_context(allowed_company_ids=[self.env.company.id, other.id])
            .create({"company_id": other.id})
        )
        wizard.fiscalyear_lock_date = "2020-12-31"
        wizard.sudo().change_lock_date()

        self.assertEqual(
            other.sudo().account_config_id.fiscalyear_lock_date,
            date(2020, 12, 31),
            "the lock date belongs to the company the wizard names",
        )
        self.assertFalse(
            self.env.company.sudo().account_config_id.fiscalyear_lock_date,
            "and must not land on whichever company happened to be active",
        )

    def test_the_wizard_shows_the_dates_of_the_company_it_names(self):
        other = self.env["res.company"].create({"name": "Elsewhere Ltd"})
        other.sudo().account_config_id.fiscalyear_lock_date = date(2019, 6, 30)
        self.env.company.sudo().account_config_id.fiscalyear_lock_date = date(
            2021, 1, 31
        )

        wizard = (
            self.env["account.change.lock.date"]
            .with_context(allowed_company_ids=[self.env.company.id, other.id])
            .create({"company_id": other.id})
        )

        self.assertEqual(wizard.fiscalyear_lock_date, date(2019, 6, 30))
        self.assertEqual(
            wizard.current_hard_lock_date, other.account_config_id.hard_lock_date
        )

    def test_the_tax_closing_warning_is_scoped_to_one_company(self):
        wizard = self.env["account.change.lock.date"].create(
            {"tax_lock_date": "2019-06-30"}
        )
        domain = wizard._get_domain_posted_tax_closings_in_locked_period()
        self.assertIn(
            ("company_id", "child_of", wizard.company_id.id),
            domain,
            "the warning reports on every company the user can see",
        )

    def test_warning_computes_over_a_batch(self):
        wizards = self.env["account.change.lock.date"].create(
            [
                {"fiscalyear_lock_date": "2019-06-30"},
                {"fiscalyear_lock_date": "2019-05-31"},
            ]
        )
        wizards._compute_show_draft_entries_warning()
        wizards._compute_show_posted_tax_closing_warning()


@tagged("post_install", "-at_install")
class TestAutoReconcileWizardScope(TransactionCase):
    def test_partner_filter_applies_without_an_account_filter(self):
        partner = self.env["res.partner"].create({"name": "Scope"})
        wizard = self.env["account.auto.reconcile.wizard"].create(
            {"to_date": "2019-12-31", "partner_ids": [(6, 0, partner.ids)]}
        )
        domain = wizard._get_domain_amls()
        self.assertTrue(
            any(leaf[0] == "partner_id" for leaf in domain if isinstance(leaf, tuple)),
            "the wizard reconciles every partner when no account is chosen",
        )


@tagged("post_install", "-at_install")
class TestReconcileWizardModelPrefill(AccountTestInvoicingCommon):
    def _wizard(self):
        move = self.env["account.move"].create(
            {
                "journal_id": self.company_data["default_journal_misc"].id,
                "date": "2019-01-01",
                "move_type": "entry",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                            "partner_id": self.partner_a.id,
                            "balance": 100.0,
                            "name": "a",
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "partner_id": self.partner_a.id,
                            "balance": -100.0,
                            "name": "b",
                        }
                    ),
                ],
            }
        )
        move.action_post()
        receivable = move.line_ids.filtered(
            lambda line: (
                line.account_id == self.company_data["default_account_receivable"]
            )
        )
        return (
            self.env["account.reconcile.wizard"]
            .with_context(active_model="account.move.line", active_ids=receivable.ids)
            .create({})
        )

    def _model(self, *accounts):
        return self.env["account.reconcile.model"].create(
            {
                "name": "prefill %d" % len(accounts),
                "line_ids": [
                    Command.create(
                        {
                            "account_id": account.id,
                            "amount_type": "percentage",
                            "amount_string": str(100 // len(accounts)),
                            "label": "line %d" % index,
                        }
                    )
                    for index, account in enumerate(accounts)
                ],
            }
        )

    def test_a_single_line_model_prefills_the_write_off(self):
        expense = self.company_data["default_account_expense"]
        wizard = self._wizard()
        wizard.reco_model_id = self._model(expense)
        wizard._onchange_reco_model_id()
        self.assertEqual(wizard.account_id, expense)
        self.assertEqual(wizard.label, "line 0")

    def test_a_multi_line_model_is_left_alone_rather_than_raising(self):
        wizard = self._wizard()
        wizard.reco_model_id = self._model(
            self.company_data["default_account_expense"],
            self.company_data["default_account_revenue"],
        )
        wizard._onchange_reco_model_id()
        self.assertFalse(
            wizard.account_id,
            "a model the wizard cannot represent must prefill nothing",
        )


@tagged("post_install", "-at_install")
class TestSigningUserFollowsTheState(AccountTestInvoicingCommon):
    def test_resetting_to_draft_clears_the_signer(self):
        signer = self.env["res.users"].create(
            {
                "name": "Signer",
                "login": "signing_state_probe",
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        self.env.company.account_config_id.write(
            {"sign_invoice": True, "signing_user": signer.id}
        )
        invoice = self.init_invoice("out_invoice", products=self.product_a, post=True)
        self.assertEqual(invoice.signing_user, signer, "posting decides the signer")

        invoice.action_draft()
        self.assertFalse(invoice.signing_user, "a draft carries no signer")


@tagged("post_install", "-at_install")
class TestTransferBalancesInEveryCurrency(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.foreign = cls.setup_other_currency(
            "EUR", rates=[("2019-01-01", 10.0), ("2019-06-01", 1.0)]
        )
        cls.journal = cls.company_data["default_journal_misc"]
        cls.counterpart = cls.company_data["default_account_revenue"]
        cls.account_from = cls.company_data["default_account_receivable"]
        cls.account_to = cls.company_data["default_account_payable"]

    def _post(self, date, rows):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "date": date,
                "line_ids": [Command.create(row) for row in rows],
            }
        )
        move.action_post()
        return move

    def test_the_transfer_balances_in_the_foreign_currency_too(self):
        source_partner = self.env["res.partner"].create({"name": "Source"})
        dest_partner = self.env["res.partner"].create({"name": "Destination"})
        source = self._post(
            "2019-01-01",
            [
                {
                    "account_id": self.account_from.id,
                    "partner_id": source_partner.id,
                    "currency_id": self.foreign.id,
                    "amount_currency": 100.0,
                    "balance": 10.0,
                },
                {"account_id": self.counterpart.id, "balance": -10.0},
            ],
        )
        destination = self._post(
            "2019-06-01",
            [
                {
                    "account_id": self.account_to.id,
                    "partner_id": dest_partner.id,
                    "currency_id": self.foreign.id,
                    "amount_currency": -50.0,
                    "balance": -50.0,
                },
                {"account_id": self.counterpart.id, "balance": 50.0},
            ],
        )
        lines = (source.line_ids | destination.line_ids).filtered(
            lambda line: line.account_id in (self.account_from | self.account_to)
        )

        wizard = (
            self.env["account.reconcile.wizard"]
            .with_context(active_model="account.move.line", active_ids=lines.ids)
            .create({})
        )
        self.assertTrue(wizard.is_transfer_required, "two accounts means a transfer")
        transfer = wizard.create_transfer()

        self.assertEqual(
            sum(transfer.line_ids.mapped("balance")),
            0.0,
            "the entry has to balance in the company currency",
        )
        per_currency = defaultdict(float)
        for line in transfer.line_ids:
            per_currency[line.currency_id] += line.amount_currency
        self.assertEqual(
            per_currency[self.foreign],
            0.0,
            "and in every other currency it names -- nothing enforces this but us",
        )
