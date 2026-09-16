from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountMoveMarinDepends(AccountTestInvoicingCommon):
    def _deps(self, fname):
        field = self.env["account.move"]._fields[fname]
        return tuple(self.env.registry.field_depends.get(field, ()))

    def test_depends_completeness(self):
        self.assertIn("state", self._deps("partner_credit_warning"))
        self.assertIn("move_type", self._deps("partner_credit_warning"))
        self.assertIn("state", self._deps("display_inactive_currency_warning"))
        self.assertIn("invoice_cash_rounding_id", self._deps("tax_totals"))
        recon = self._deps("has_reconciled_entries")
        self.assertIn("line_ids.matched_debit_ids", recon)
        self.assertIn("line_ids.matched_credit_ids", recon)
        self.assertIn("line_ids.amount_currency", self._deps("payment_term_details"))
        self.assertIn("move_type", self._deps("show_delivery_date"))

    def test_show_delivery_date_recomputes_on_move_type_change(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=False
        )
        invoice.delivery_date = fields.Date.context_today(invoice)
        self.assertTrue(
            invoice.show_delivery_date, "a sale document with a delivery date shows it"
        )
        invoice.move_type = "entry"
        self.assertFalse(
            invoice.show_delivery_date,
            "show_delivery_date must refresh when the move type stops being a sale",
        )

    def test_partner_credit_warning_clears_on_post(self):
        self.env.company.account_use_credit_limit = True
        self.partner_a.credit_limit = 1.0
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[1000.0], post=False
        )
        self.assertTrue(invoice.partner_credit_warning, "over-limit draft must warn")
        invoice.action_post()
        self.assertFalse(
            invoice.partner_credit_warning,
            "warning must clear once posted (state is a dependency)",
        )

    def test_has_reconciled_entries_updates_on_reconcile(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        self.assertFalse(invoice.has_reconciled_entries)
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create({})._create_payments()
        self.assertTrue(
            invoice.has_reconciled_entries,
            "field must flip once the invoice is reconciled with its payment",
        )

    def test_outstanding_widget_batched_across_moves(self):
        inv1 = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        inv2 = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[200.0], post=True
        )
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": 50.0,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        payment.action_post()
        receivable_line = payment.move_id.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )

        moves = inv1 + inv2
        moves.invalidate_recordset(["invoice_outstanding_credits_debits_widget"])
        for inv in moves:
            widget = inv.invoice_outstanding_credits_debits_widget
            self.assertTrue(widget, "each invoice must surface the outstanding payment")
            self.assertIn(
                receivable_line.id,
                [content["id"] for content in widget["content"]],
                "the batched result must include the partner's outstanding credit",
            )

    def test_normalize_vals_does_not_mutate_caller(self):
        vals = {
            "move_type": "out_invoice",
            "invoice_line_ids": [
                Command.create({"name": "A", "quantity": 1, "price_unit": 10})
            ],
            "line_ids": [
                Command.create({"name": "B", "quantity": 1, "price_unit": 20})
            ],
        }
        original_line_ids = vals["line_ids"]
        result = self.env["account.move"]._normalize_vals(vals)
        self.assertIn("invoice_line_ids", vals, "caller dict must be untouched")
        self.assertEqual(len(vals["line_ids"]), 1, "caller list must not grow")
        self.assertIs(vals["line_ids"], original_line_ids)
        self.assertNotIn("invoice_line_ids", result)
        self.assertEqual(len(result["line_ids"]), 2)

    def test_reverse_moves_does_not_mutate_default_values(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        default_values = {"ref": "keep-me"}
        invoice._reverse_moves([default_values])
        self.assertEqual(
            default_values,
            {"ref": "keep-me"},
            "caller's default_values dict must not be mutated in place",
        )

    def test_partial_deductibility_group_reveal_extracted(self):
        move_model = self.env["account.move"]
        self.assertTrue(
            hasattr(move_model, "_reveal_partial_deductibility_group"),
            "group reveal must be an explicit, overridable hook",
        )
        user = self.env["res.users"].create(
            {
                "name": "Poster",
                "login": "marin_poster_test",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.company.ids)],
                "group_ids": [
                    Command.link(self.env.ref("account.group_account_invoice").id)
                ],
            }
        )
        group_xmlid = "account.group_partial_purchase_deductibility"
        self.assertFalse(user.has_group(group_xmlid))
        bill = move_model.with_user(user).create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "partial",
                            "quantity": 1,
                            "price_unit": 100,
                            "tax_ids": [],
                            "deductible_amount": 50,
                        }
                    )
                ],
            }
        )
        bill.with_user(user).action_post()
        user.invalidate_recordset(["group_ids"])
        self.assertTrue(
            user.has_group(group_xmlid),
            "posting a partially-deductible bill still reveals the feature",
        )

    def test_display_state_query_sees_unflushed_state(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        self.env.flush_all()
        invoice.action_cancel()
        self.assertEqual(invoice.display_state, "cancel")
        self.assertEqual(
            self.env["account.move"].search(
                [("id", "=", invoice.id), ("display_state", "=", "cancel")]
            ),
            invoice,
            "search on display_state must flush the columns its SQL reads",
        )
        self.assertEqual(
            self.env["account.move"]._read_group(
                [("id", "=", invoice.id)], ["display_state"]
            ),
            [("cancel",)],
            "grouping on display_state must flush too",
        )

    def test_move_sent_values_query_sees_unflushed_is_move_sent(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=True
        )
        self.env.flush_all()
        invoice.is_move_sent = True
        self.assertEqual(invoice.move_sent_values, "sent")
        self.assertEqual(
            self.env["account.move"]._read_group(
                [("id", "=", invoice.id)], ["move_sent_values"]
            ),
            [("sent",)],
        )

    def test_display_state_compute_matches_sql_for_every_combination(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=False
        )
        self.env.flush_all()
        payment_states = [
            value
            for value, _label in self.env["account.move"]
            ._fields["payment_state"]
            .selection
        ]
        mismatches = []
        for state in ("draft", "posted", "cancel"):
            for payment_state in payment_states:
                for is_sent in (True, False):
                    self.env.cr.execute(
                        "UPDATE account_move SET state = %s, payment_state = %s, "
                        "is_move_sent = %s WHERE id = %s",
                        (state, payment_state, is_sent, invoice.id),
                    )
                    invoice.invalidate_recordset()
                    computed = invoice.display_state
                    if not self.env["account.move"].search(
                        [
                            ("id", "=", invoice.id),
                            ("display_state", "=", computed),
                        ]
                    ):
                        mismatches.append((state, payment_state, is_sent, computed))
        self.assertFalse(mismatches, "compute and SQL disagree for: %s" % mismatches)

    def test_payment_term_early_discount_rules_hold_on_write(self):
        term = self.env["account.payment.term"].create(
            {
                "name": "early",
                "early_discount": True,
                "discount_percentage": 2.0,
                "discount_days": 7,
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 100.0, "nb_days": 30}
                    )
                ],
            }
        )
        with self.assertRaises(
            ValidationError, msg="a negative discount must be refused"
        ):
            term.discount_percentage = -50.0
            self.env.flush_all()
        term.invalidate_recordset()
        with self.assertRaises(
            ValidationError, msg="a zero-day discount must be refused"
        ):
            term.discount_days = 0
            self.env.flush_all()

    def test_reconcile_model_amount_rules_hold_on_write(self):
        model = self.env["account.reconcile.model"].create(
            {"name": "rm", "company_id": self.env.company.id}
        )
        line = self.env["account.reconcile.model.line"].create(
            {
                "model_id": model.id,
                "account_id": self.company_data["default_account_expense"].id,
                "amount_type": "regex",
                "amount_string": r"([\d,]+)",
            }
        )
        self.env.flush_all()
        with self.assertRaises(UserError):
            line.amount_type = "percentage"
            self.env.flush_all()

    def test_conflicting_line_commands_raise_a_handled_error(self):
        invoice = self.init_invoice(
            "out_invoice", partner=self.partner_a, amounts=[100.0], post=False
        )
        with self.assertRaises(UserError):
            invoice.write(
                {
                    "invoice_line_ids": [Command.set([])],
                    "line_ids": [Command.create({})],
                }
            )

    def test_remove_empty_lines_spares_free_of_charge_lines(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-03-03",
                "invoice_line_ids": [
                    Command.create(
                        {"name": "free sample A", "quantity": 3, "price_unit": 0.0}
                    ),
                    Command.create(
                        {"name": "free sample B", "quantity": 2, "price_unit": 0.0}
                    ),
                    Command.create(
                        {"name": "paid item", "quantity": 1, "price_unit": 10.0}
                    ),
                ],
            }
        )
        self.assertNotIn(
            "account_remove_empty_lines",
            bill._get_alerts(),
            "described, quantified, free-of-charge lines are content, not emptiness",
        )

    def test_remove_empty_lines_still_offers_to_drop_blank_lines(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-03-03",
                "invoice_line_ids": [
                    Command.create({}),
                    Command.create({}),
                    Command.create(
                        {"name": "paid item", "quantity": 1, "price_unit": 10.0}
                    ),
                ],
            }
        )
        alerts = bill._get_alerts()
        self.assertIn("account_remove_empty_lines", alerts)
        self.assertEqual(
            self.env["account.move.line"]
            .browse(alerts["account_remove_empty_lines"]["action_call"][2])
            .mapped("name"),
            [False, False],
            "only the untouched rows are proposed for removal",
        )
