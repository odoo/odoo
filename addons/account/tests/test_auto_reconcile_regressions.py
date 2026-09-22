from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common_reconcile import TestBankRecWidgetCommon


@tagged("post_install", "-at_install")
class TestAutoReconcileRegressions(TestBankRecWidgetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_journal = cls.company_data["default_journal_bank"]

    def _invoice_with_ref(self, ref, amount, move_type="out_invoice"):
        account = (
            self.company_data["default_account_revenue"]
            if move_type == "out_invoice"
            else self.company_data["default_account_expense"]
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.partner_a.id,
                "ref": ref,
                "invoice_date": "2019-01-01",
                "date": "2019-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "l",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": account.id,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def test_overlapping_references_do_not_crash(self):
        refs = ["AAAAAAAA", "BBBAAAAAAAA", "CCCAAAAAAAA"]
        for ref in refs:
            self._invoice_with_ref(ref, 100.0)
        st_line = self._create_st_line(
            300.0, payment_ref=" ".join(refs), partner_id=self.partner_a.id
        )

        for ref in refs:
            self.assertTrue(
                st_line._is_properly_surrounded(st_line.payment_ref, ref),
                "the test is only meaningful while all three words reach the loop",
            )

        st_line._try_auto_reconcile_statement_lines()
        self.assertTrue(st_line.is_reconciled)

    def test_failing_line_does_not_retire_its_batch(self):
        StatementLine = type(self.env["account.bank.statement.line"])
        genuine = StatementLine._try_auto_reconcile_statement_lines

        def explode(records, *args, **kwargs):
            if len(records) > 1:
                raise ValueError("boom")
            return genuine(records, *args, **kwargs)

        self._invoice_with_ref("ZZZZZZZZZZ", 55.0)
        good = self._create_st_line(
            55.0, payment_ref="PAY ZZZZZZZZZZ", partner_id=self.partner_a.id
        )
        other = self._create_st_line(
            13.0, payment_ref="UNMATCHABLE", partner_id=self.partner_a.id
        )

        self.patch(StatementLine, "_try_auto_reconcile_statement_lines", explode)
        self.env[
            "account.bank.statement.line"
        ]._cron_try_auto_reconcile_statement_lines(batch_size=100)
        self.env.invalidate_all()

        self.assertTrue(
            good.is_reconciled,
            "the batch failed as a whole, so each line is retried alone and this one works",
        )
        self.assertTrue(
            good.line_ids.filtered("reconciled_lines_ids"),
            "the line was stamped as checked without ever being matched",
        )
        self.assertTrue(
            other.cron_last_check,
            "a line the CRON has looked at is marked, matched or not",
        )

    def test_payment_reference_matching_is_sign_symmetric(self):
        def run(move_type, sign, refs):
            for ref in refs:
                self._invoice_with_ref(ref, 100.0, move_type=move_type)
            self._invoice_with_ref("UNRELATEDREF", 77.0, move_type=move_type)
            st_line = self._create_st_line(
                sign * 200.0,
                payment_ref="PAYMENT %s AND %s" % tuple(refs),
                partner_id=self.partner_a.id,
            )
            st_line._try_auto_reconcile_statement_lines()
            return len(st_line.line_ids.filtered("reconciled_lines_ids"))

        inbound = run("out_invoice", 1, ["INVREFAAA", "INVREFBBB"])
        outbound = run("in_invoice", -1, ["BILLREFAAA", "BILLREFBBB"])
        self.assertEqual(inbound, 2, "both invoices are named in the label")
        self.assertEqual(
            outbound, inbound, "the outbound mirror must match the same number of lines"
        )

    def test_import_does_not_retire_unrelated_lines(self):
        existing = self.env["account.bank.statement.line"]
        for index in range(3):
            existing |= self._create_st_line(
                -5.0, payment_ref="PREEXISTING %s" % index, update_create_date=False
            )

        self.env["account.bank.statement.line"].with_context(
            auto_statement_processing=True
        ).create(
            [
                {
                    "journal_id": self.bank_journal.id,
                    "payment_ref": "IMPORT %s" % index,
                    "amount": -7.0,
                    "date": "2019-01-01",
                }
                for index in range(5)
            ]
        )

        self.assertFalse(
            existing.filtered("cron_last_check"),
            "the import retired statement lines it was never given",
        )

    def _run_on_demand(self, from_date="2019-01-01", to_date="2019-12-31"):
        wizard = self.env["account.bank.auto.reconcile.wizard"].create(
            {
                "journal_id": self.bank_journal.id,
                "from_date": from_date,
                "to_date": to_date,
            }
        )
        return wizard.action_auto_reconcile()

    def test_on_demand_auto_reconcile_reaches_lines_the_cron_retired(self):
        """The whole point of the on-demand run.

        `_cron_try_auto_reconcile_statement_lines` only ever selects lines whose
        `cron_last_check` is unset, so a reconciliation model written after the
        fact can never be applied to an older transaction. The wizard searches
        by journal and date instead, so a retired line is reachable again.
        """
        self._invoice_with_ref("LATERULEAAA", 42.0)
        st_line = self._create_st_line(
            42.0, payment_ref="PAY LATERULEAAA", partner_id=self.partner_a.id
        )
        st_line.cron_last_check = self.env.cr.now()

        self.env[
            "account.bank.statement.line"
        ]._cron_try_auto_reconcile_statement_lines(batch_size=100)
        self.env.invalidate_all()
        self.assertFalse(
            st_line.is_reconciled,
            "the cron cannot see a line it has already stamped",
        )

        self._run_on_demand()
        self.env.invalidate_all()

        self.assertTrue(
            st_line.is_reconciled,
            "the on-demand run searches by journal and date, not by cron_last_check",
        )

    def test_on_demand_auto_reconcile_isolates_a_failing_line_without_retiring_it(self):
        """One bad transaction costs one transaction, and stays in the cron's queue.

        `_try_auto_reconcile_statement_lines` works on the whole recordset and
        aborts on the first line that raises, which is why the cron retries line
        by line. The on-demand run shares that protection but must not stamp
        `cron_last_check`: an ad-hoc pass that happened to hit a bad line must
        not drop it out of the nightly cron for good.
        """
        StatementLine = type(self.env["account.bank.statement.line"])
        genuine = StatementLine._try_auto_reconcile_statement_lines

        self._invoice_with_ref("GOODREFAAAA", 55.0)
        good = self._create_st_line(
            55.0, payment_ref="PAY GOODREFAAAA", partner_id=self.partner_a.id
        )
        bad = self._create_st_line(
            13.0, payment_ref="EXPLODE", partner_id=self.partner_a.id
        )

        def explode(records, *args, **kwargs):
            if "EXPLODE" in records.mapped("payment_ref"):
                raise ValueError("boom")
            return genuine(records, *args, **kwargs)

        self.patch(StatementLine, "_try_auto_reconcile_statement_lines", explode)
        self._run_on_demand()
        self.env.invalidate_all()

        self.assertTrue(
            good.is_reconciled,
            "the failing line is isolated in its own savepoint, so this one still runs",
        )
        self.assertFalse(
            bad.cron_last_check,
            "an on-demand run does not retire a line from the nightly cron",
        )

    def test_on_demand_auto_reconcile_wizard_defaults_resolve(self):
        """The dialog opens on a one-month window; a raising default breaks it for everyone."""
        defaults = self.env["account.bank.auto.reconcile.wizard"].default_get(
            ["company_id", "from_date", "to_date"]
        )
        self.assertEqual(defaults["company_id"], self.env.company.id)
        self.assertLess(defaults["from_date"], defaults["to_date"])
