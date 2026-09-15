from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools.rendering_tools import QWebError

from odoo.addons.account_payment_provider.tests.common import AccountPaymentCommon


@tagged("-at_install", "post_install")
class TestAccountPayment(AccountPaymentCommon):
    def test_cancelled_invoice_rejects_payment_initiation(self):
        invoice = self.misc_entry
        invoice.action_cancel()
        for flow in ("direct", "redirect", "token"):
            with self.subTest(flow=flow):
                with self.assertRaises(ValidationError), self.cr.savepoint():
                    self._create_transaction(
                        flow, invoice_ids=[Command.set(invoice.ids)]
                    )
        self.assertFalse(invoice.transaction_ids)

    def test_no_amount_available_for_refund_when_no_tx(self):
        payment = self.env["account.payment"].create({"amount": 10})
        self.assertEqual(
            payment.amount_available_for_refund,
            0,
            msg="The value of `amount_available_for_refund` should be 0 when the payment was not"
            " created by a transaction.",
        )

    def test_no_amount_available_for_refund_when_not_supported(self):
        self.provider.support_refund = "none"
        tx = self._create_transaction("redirect", state="done")
        tx._post_process()  # Create the payment
        self.assertEqual(
            tx.payment_id.amount_available_for_refund,
            0,
            msg="The value of `amount_available_for_refund` should be 0 when the provider doesn't "
            "support refunds.",
        )

    def test_full_amount_available_for_refund_when_not_yet_refunded(self):
        self.provider.support_refund = "full_only"  # Should simply not be False
        tx = self._create_transaction("redirect", state="done")
        tx._post_process()  # Create the payment
        self.assertAlmostEqual(
            tx.payment_id.amount_available_for_refund,
            tx.amount,
            places=2,
            msg="The value of `amount_available_for_refund` should be that of `total` when there "
            "are no linked refunds.",
        )

    def test_full_amount_available_for_refund_when_refunds_are_pending(self):
        self.provider.write(
            {
                "support_refund": "full_only",  # Should simply not be False
                "support_manual_capture": "partial",  # To create transaction in the 'authorized' state
            }
        )
        tx = self._create_transaction("redirect", state="done")
        tx._post_process()  # Create the payment
        for reference_index, state in enumerate(("draft", "pending", "authorized")):
            self._create_transaction(
                "dummy",
                amount=-tx.amount,
                reference=f"R-{tx.reference}-{reference_index + 1}",
                state=state,
                operation="refund",  # Override the computed flow
                source_transaction_id=tx.id,
            )
        self.assertAlmostEqual(
            tx.payment_id.amount_available_for_refund,
            tx.payment_id.amount,
            places=2,
            msg="The value of `amount_available_for_refund` should be that of `total` when all the "
            "linked refunds are pending (not in the state 'done').",
        )

    def test_no_amount_available_for_refund_when_fully_refunded(self):
        self.provider.support_refund = "full_only"  # Should simply not be False
        tx = self._create_transaction("redirect", state="done")
        tx._post_process()  # Create the payment
        self._create_transaction(
            "dummy",
            amount=-tx.amount,
            reference=f"R-{tx.reference}",
            state="done",
            operation="refund",  # Override the computed flow
            source_transaction_id=tx.id,
        )._post_process()
        self.assertEqual(
            tx.payment_id.amount_available_for_refund,
            0,
            msg="The value of `amount_available_for_refund` should be 0 when there is a linked "
            "refund of the full amount that is confirmed (state 'done').",
        )

    def test_no_full_amount_available_for_refund_when_partially_refunded(self):
        self.provider.support_refund = "partial"
        tx = self._create_transaction("redirect", state="done")
        tx._post_process()  # Create the payment
        self._create_transaction(
            "dummy",
            amount=-(tx.amount / 10),
            reference=f"R-{tx.reference}",
            state="done",
            operation="refund",  # Override the computed flow
            source_transaction_id=tx.id,
        )._post_process()
        self.assertAlmostEqual(
            tx.payment_id.amount_available_for_refund,
            tx.payment_id.amount - (tx.amount / 10),
            places=2,
            msg="The value of `amount_available_for_refund` should be equal to the total amount "
            "minus the sum of the absolute amount of the refunds that are confirmed (state "
            "'done').",
        )

    def test_refunds_count(self):
        self.provider.support_refund = "full_only"  # Should simply not be False
        tx = self._create_transaction("redirect", state="done")
        tx._post_process()  # Create the payment
        for reference_index, operation in enumerate(
            ("online_redirect", "online_direct", "online_token", "validation", "refund")
        ):
            self._create_transaction(
                "dummy",
                reference=f"R-{tx.reference}-{reference_index + 1}",
                state="done",
                operation=operation,  # Override the computed flow
                source_transaction_id=tx.id,
            )._post_process()

        self.assertEqual(
            tx.payment_id.refunds_count,
            1,
            msg="The refunds count should only consider transactions with operation 'refund'.",
        )

    def test_refund_message_author_is_logged_in_user(self):
        """Ensure that the chatter message author is the user processing the refund."""
        self.provider.support_refund = "full_only"

        tx = self._create_transaction("redirect", state="done")
        tx._post_process()

        with patch.object(
            self.env.registry["account.payment"], "message_post", autospec=True
        ) as message_post_mock:
            tx.action_refund()
            author_id = message_post_mock.call_args[1].get("author_id")

        self.assertEqual(author_id, self.user.partner_id.id)

    def test_action_post_calls_send_payment_request_only_once(self):
        payment_token = self._create_token()
        payment_without_token = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "amount": 2000.0,
                "date": "2019-01-01",
                "currency_id": self.currency.id,
                "partner_id": self.partner.id,
                "journal_id": self.provider.journal_id.id,
                "payment_channel_id": self.inbound_payment_channel.id,
            }
        )
        payment_with_token = payment_without_token.copy()
        payment_with_token.payment_token_id = payment_token.id

        with patch(
            "odoo.addons.payment.models.payment_transaction.PaymentTransaction"
            "._charge_with_token"
        ) as patched:
            payment_without_token.action_post()
            patched.assert_not_called()
            payment_with_token.action_post()
            patched.assert_called_once()

    def test_online_payment_error_no_duplicate_message_when_fully_paid(self):
        """Test that _get_online_payment_error does not emit both 'There is no amount
        to be paid.' and 'This invoice has already been paid.' for the same
        zero-residual cause."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create({"name": "test line", "price_unit": 100.0}),
                ],
            }
        )
        invoice.action_post()
        errors_before_payment = invoice._get_online_payment_error()
        self.assertNotIn("This invoice has already been paid.", errors_before_payment)

        self._register_payment(invoice)
        self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))
        errors_after_payment = invoice._get_online_payment_error()
        self.assertIn("This invoice has already been paid.", errors_after_payment)
        self.assertEqual(
            errors_after_payment.count("There is no amount to be paid."),
            0,
            "The zero-residual cause should only produce one message ('already paid'), "
            "not two overlapping ones.",
        )

    def test_suitable_payment_token_ids_grouped_by_company_partner_provider(self):
        """Test that _compute_suitable_payment_token_ids returns the right tokens for
        each distinct (company, partner, provider) group when computed on a batch of
        several account.payment records sharing the same group."""
        provider_method_line = (
            self.provider.journal_id.inbound_payment_channel_ids.filtered(
                lambda l: l.payment_provider_id == self.provider
            )
        )
        token = self._create_token()
        other_partner = self.partner.copy()
        other_token = self._create_token(partner_id=other_partner.id)
        payments = self.env["account.payment"].create(
            [
                {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "amount": 100.0,
                    "date": "2019-01-01",
                    "currency_id": self.currency.id,
                    "partner_id": self.partner.id,
                    "journal_id": self.provider.journal_id.id,
                    "payment_channel_id": provider_method_line.id,
                },
                {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "amount": 200.0,
                    "date": "2019-01-01",
                    "currency_id": self.currency.id,
                    "partner_id": self.partner.id,
                    "journal_id": self.provider.journal_id.id,
                    "payment_channel_id": provider_method_line.id,
                },
                {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "amount": 300.0,
                    "date": "2019-01-01",
                    "currency_id": self.currency.id,
                    "partner_id": other_partner.id,
                    "journal_id": self.provider.journal_id.id,
                    "payment_channel_id": provider_method_line.id,
                },
            ]
        )
        same_group_1, same_group_2, other_group = payments
        self.assertEqual(same_group_1.suitable_payment_token_ids, token)
        self.assertEqual(same_group_2.suitable_payment_token_ids, token)
        self.assertEqual(other_group.suitable_payment_token_ids, other_token)

    def test_payment_action_void_ensures_single_record(self):
        """Test that payment_action_void raises on a multi-record recordset, matching
        its sibling payment_action_capture, instead of silently voiding transactions
        across several invoices at once."""
        invoice_1 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create({"name": "line 1", "price_unit": 50.0}),
                ],
            }
        )
        invoice_2 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create({"name": "line 2", "price_unit": 50.0}),
                ],
            }
        )
        with self.assertRaises(ValueError):
            (invoice_1 + invoice_2).payment_action_void()
        # Single-record call still works.
        invoice_1.payment_action_void()

    def test_no_payment_for_validations(self):
        tx = self._create_transaction(
            flow="dummy", operation="validation"
        )  # Overwrite the flow
        tx._post_process()
        payment_count = self.env["account.payment"].search_count(
            [("transaction_id", "=", tx.id)]
        )
        self.assertEqual(
            payment_count, 0, msg="validation transactions should not create payments"
        )

    def test_payments_for_source_tx_with_children(self):
        self.provider.support_manual_capture = "partial"
        source_tx = self._create_transaction(flow="direct", state="authorized")
        child_tx_1 = source_tx._create_child_transaction(100)
        child_tx_1._set_done()
        child_tx_2 = source_tx._create_child_transaction(source_tx.amount - 100)
        self.assertEqual(
            source_tx.state,
            "authorized",
            msg="The source transaction should be authorized when the total processed amount of its"
            " children is not equal to the source amount.",
        )
        child_tx_2._set_canceled()
        self.assertEqual(
            source_tx.state,
            "done",
            msg="The source transaction should be done when the total processed amount of its"
            " children is equal to the source amount.",
        )
        child_tx_1._post_process()
        self.assertTrue(
            child_tx_1.payment_id, msg="Child transactions should create payments."
        )
        source_tx._post_process()
        self.assertFalse(
            source_tx.payment_id,
            msg="source transactions with done or cancel children should not create payments.",
        )

    def test_prevent_unlink_apml_with_active_provider(self):
        """Test that deleting an `account.payment.channel` linked to an active provider raises."""
        self.assertEqual(self.dummy_provider.state, "test")
        with self.assertRaises(UserError):
            self.dummy_provider.journal_id.inbound_payment_channel_ids.unlink()

    def test_provider_journal_assignation(self):
        """Test the computation of the 'journal_id' field and so, the link with the accounting side."""

        def get_payment_channel(provider):
            return self.env["account.payment.channel"].search(
                [("payment_provider_id", "=", provider.id)]
            )

        with self.mocked_get_payment_method_information():
            journal = self.company_data["default_journal_bank"]
            provider = self.provider
            self.assertRecordValues(provider, [{"journal_id": journal.id}])

            # Test changing the journal.
            copy_journal = journal.copy()
            payment_channel = get_payment_channel(provider)
            provider.journal_id = copy_journal
            self.assertRecordValues(provider, [{"journal_id": copy_journal.id}])
            self.assertRecordValues(payment_channel, [{"journal_id": copy_journal.id}])

            # Test duplication of the provider.
            payment_channel.payment_account_id = (
                self.inbound_payment_channel.payment_account_id
            )
            copy_provider = self.provider.copy()
            self.assertRecordValues(copy_provider, [{"journal_id": False}])
            copy_provider.state = "test"
            self.assertRecordValues(copy_provider, [{"journal_id": journal.id}])
            self.assertRecordValues(
                get_payment_channel(copy_provider),
                [
                    {
                        "journal_id": journal.id,
                        "payment_account_id": payment_channel.payment_account_id.id,
                    }
                ],
            )

            # We are able to have both on the same journal...
            with self.assertRaises(ValidationError):
                # ...but not having both with the same name.
                provider.journal_id = journal

            method_line = get_payment_channel(copy_provider)
            method_line.name = "dummy (copy)"
            provider.journal_id = journal

            # You can't have twice the same acquirer on the same journal.
            copy_provider_pml = get_payment_channel(copy_provider)
            with self.assertRaises(ValidationError):
                journal.inbound_payment_channel_ids = [
                    Command.update(
                        copy_provider_pml.id, {"payment_provider_id": provider.id}
                    )
                ]

    def test_generate_payment_link_with_no_invoice_line(self):
        invoice = self.misc_entry
        invoice.line_ids.unlink()
        payment_values = invoice._prepare_payment_link_vals()

        self.assertDictEqual(
            payment_values,
            {
                "currency_id": invoice.currency_id.id,
                "partner_id": invoice.partner_id.id,
                "open_installments": [],
                "amount": None,
                "amount_max": None,
            },
        )

    def test_payment_invoice_same_receivable(self):
        """Test that the payment of a transaction takes its destination account from the invoice
        line rather than from the partner's receivable account."""
        payment_term = self.env["account.payment.term"].create(
            {
                "name": "early_payment_term",
                "company_id": self.company_data["company"].id,
                "discount_percentage": 10,
                "discount_days": 10,
                "early_discount": True,
            }
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "currency_id": self.currency.id,
                "invoice_payment_term_id": payment_term.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "test line",
                            "price_unit": 100.0,
                            "tax_ids": [
                                Command.set(self.company_data["default_tax_sale"].ids)
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "test line 2",
                            "price_unit": 100.0,
                            "tax_ids": [
                                Command.set(self.company_data["default_tax_sale"].ids)
                            ],
                        }
                    ),
                ],
            }
        )

        self.partner.property_account_receivable_id = self.env[
            "account.account"
        ].search([("name", "=", "Account Payable")], limit=1)
        payment = self._create_transaction(
            reference="payment_3",
            flow="direct",
            state="done",
            amount=invoice._get_early_payment_discount_details()["amount_due"],
            invoice_ids=[invoice.id],
            partner_id=self.partner.id,
        )._create_payment()

        self.assertNotEqual(
            self.partner.property_account_receivable_id, payment.destination_account_id
        )
        self.assertEqual(
            payment.destination_account_id, invoice.line_ids[-1].account_id
        )

    def test_vendor_payment_name_remains_same_after_repost(self):
        """Test that reposting a vendor payment keeps its name, unless the journal changed."""
        journal = self.company_data["default_journal_bank"]

        payment = self.env["account.payment"].create(
            {
                "partner_id": self.partner.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "amount": 10,
                "journal_id": journal.id,
                "payment_channel_id": journal.inbound_payment_channel_ids[0].id,
            }
        )
        payment.action_post()

        original_name = payment.move_id.name

        payment2 = self.env["account.payment"].create(
            {
                "partner_id": self.partner.id,
                "partner_type": "supplier",
                "payment_type": "outbound",
                "amount": 20,
                "journal_id": journal.id,
                "payment_channel_id": journal.inbound_payment_channel_ids[0].id,
            }
        )

        payment2.action_post()
        payment.move_id.action_draft()
        payment.move_id.line_ids.unlink()
        payment.amount = 30
        payment.move_id._compute_name()
        payment.move_id._post()

        self.assertEqual(
            payment.move_id.name,
            original_name,
            "Payment name should remain the same after reposting",
        )

        # Now try to change the journal, and check if the name is now updated
        payment.move_id.action_draft()
        new_journal = journal.copy()
        new_payment_channel = new_journal.outbound_payment_channel_ids[0]
        new_payment_channel.write(
            {"payment_account_id": payment.payment_channel_id.payment_account_id.id}
        )
        payment.write(
            {
                "journal_id": new_journal.id,
                "payment_channel_id": new_payment_channel.id,
            }
        )
        payment.move_id.action_post()
        self.assertNotEqual(
            payment.move_id.name,
            original_name,
            "Payment name should be updated after changing the journal",
        )

    def test_post_process_does_not_fail_on_cancelled_invoice(self):
        """Test that `_post_process` does not raise when the transaction is confirmed after its
        invoice was cancelled."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "test line",
                            "price_unit": 100.0,
                        }
                    ),
                ],
            }
        )
        tx = self._create_transaction(
            flow="direct",
            state="pending",
            invoice_ids=[invoice.id],
        )
        invoice.action_cancel()
        tx._set_done()
        # _post_process() shouldn't raise an error even though the invoice is cancelled
        tx._post_process()
        self.assertEqual(tx.payment_id.state, "in_process")

    def test_post_process_only_posts_own_transaction_invoices(self):
        """Test that `_post_process` on a batch of transactions only posts the invoices linked
        to the transaction that actually reached the `done` state, not invoices linked to other
        (non-done) transactions in the same batch."""
        done_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create({"name": "done tx line", "price_unit": 100.0}),
                ],
            }
        )
        pending_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create({"name": "pending tx line", "price_unit": 50.0}),
                ],
            }
        )
        done_tx = self._create_transaction(
            flow="direct",
            state="pending",
            reference="Test Transaction Done",
            invoice_ids=[done_invoice.id],
        )
        pending_tx = self._create_transaction(
            flow="direct",
            state="pending",
            reference="Test Transaction Pending",
            invoice_ids=[pending_invoice.id],
        )
        done_tx._set_done()
        # Only done_tx is 'done'; call _post_process on the whole batch, as
        # account_payment.py's action_post() does when several token-based
        # payments are posted together.
        (done_tx + pending_tx)._post_process()
        self.assertEqual(
            done_invoice.state,
            "posted",
            "The invoice linked to the done transaction should be posted.",
        )
        self.assertEqual(
            pending_invoice.state,
            "draft",
            "The invoice linked to the still-pending transaction should NOT be posted "
            "as a side effect of processing an unrelated done transaction in the same batch.",
        )

    def test_create_payment_no_forced_destination_account_when_invoices_differ(self):
        """Test that `_create_payment` does not force `destination_account_id` to one
        invoice's receivable account when the transaction's invoices don't all share the
        same one, so it falls back to account.payment's own partner-based compute instead
        of silently excluding the other invoice's lines from reconciliation."""
        invoice_1 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create({"name": "line 1", "price_unit": 50.0}),
                ],
            }
        )
        invoice_2 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create({"name": "line 2", "price_unit": 50.0}),
                ],
            }
        )
        (invoice_1 + invoice_2).action_post()
        # Both diverge from the partner's actual default receivable account,
        # so an "arbitrary pick" (whichever invoice's line happens to be
        # first) is distinguishable from the correct partner-based fallback.
        other_receivable_1 = self.company_data["default_account_receivable"].copy()
        other_receivable_2 = self.company_data["default_account_receivable"].copy()
        invoice_1.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        ).account_id = other_receivable_1
        invoice_2.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        ).account_id = other_receivable_2

        tx = self._create_transaction(
            "direct",
            state="done",
            amount=100.0,
            invoice_ids=[invoice_1.id, invoice_2.id],
        )
        payment = tx._create_payment()
        self.assertEqual(
            payment.destination_account_id,
            invoice_1.partner_id.property_account_receivable_id,
            "With diverging invoice accounts, destination_account_id should fall back to "
            "the partner's own receivable account (account.payment's default compute), "
            "not be forced to whichever invoice happened to be first.",
        )

    def test_payment_token_for_invoice_partner_is_available(self):
        """Test that the payment token of the invoice partner is available"""
        Wizard = self.env["account.payment.register"].with_context(
            active_model="account.move"
        )
        with self.mocked_get_payment_method_information():
            bank_journal = self.company_data["default_journal_bank"]
            payment_channel = bank_journal.inbound_payment_channel_ids.filtered(
                lambda line: line.payment_provider_id == self.dummy_provider
            )
            self.assertTrue(payment_channel)

            def payment_register_wizard(invoices):
                return Wizard.with_context(active_ids=invoices.ids).create(
                    {
                        "payment_channel_id": payment_channel.id,
                    }
                )

            child_partner, other_child = self.env["res.partner"].create(
                [
                    {
                        "name": name,
                        "is_company": False,
                        "parent_id": self.partner.id,
                    }
                    for name in ("child_partner", "other_child")
                ]
            )
            invoice = self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": child_partner.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "test line",
                                "price_unit": 100.0,
                            }
                        ),
                    ],
                }
            )
            invoice.action_post()
            payment_token = self._create_token(partner_id=child_partner.id)
            wizard = payment_register_wizard(invoice)
            self.assertRecordValues(
                wizard,
                [
                    {
                        "suitable_payment_token_ids": payment_token.ids,
                        "payment_token_id": payment_token.id,
                    }
                ],
            )

            # Check that tokens assigned to the specific partner as well as their
            # commercial partner can be selected.
            parent_token = self._create_token(partner_id=self.partner.id)
            wizard = payment_register_wizard(invoice)
            self.assertEqual(
                wizard.suitable_payment_token_ids, payment_token + parent_token
            )

            # Check that payments for multiple invoices with multiple partners
            # only retrieve tokens assigned to a common commercial partner.
            other_invoice = invoice.copy({"partner_id": other_child.id})
            other_invoice.action_post()
            wizard = payment_register_wizard(invoice + other_invoice)
            self.assertEqual(wizard.suitable_payment_token_ids, parent_token)

    def test_generate_and_send_invoice_with_qr_code(self):
        """Test generating & sending invoices with QR codes enabled."""
        self.env.company.link_qr_code = True
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create({"name": "$100", "price_unit": 100.0})
                ],
            }
        )
        move.action_post()

        with patch.object(
            move.__class__,
            "_generate_portal_payment_qr",
            wraps=move._generate_portal_payment_qr,
        ) as payment_qr_mock:
            self._assert_does_not_raise(
                QWebError,
                self.env["mixin.account.move.send"]._generate_and_send_invoices(move),
            )
            self.assertTrue(payment_qr_mock.called)

    def test_partial_reconcile_with_payments_coming_from_provider(self):
        """Test that partial reconciliation is not allowed on payments coming from a provider."""
        provider = self.env["payment.provider"].create(
            {
                "name": "Test",
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "journal_id": self.company_data["default_journal_sale"].id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 100,
                        }
                    )
                ],
            }
        )
        payment_transaction = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env.ref("payment.payment_method_unknown").id,
                "invoice_ids": [invoice.id],
                "partner_id": self.partner_a.id,
                "amount": 200,
                "currency_id": invoice.currency_id.id,
            }
        )
        payment_transaction._create_payment(
            payment_channel_id=self.company_data["default_journal_bank"]
            .inbound_payment_channel_ids[0]
            .id
        )
        payment_transaction._post_process()
        payment = payment_transaction.payment_id
        invoice.action_post()
        payment.action_post()
        statement_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.company_data["default_journal_bank"].id,
                "date": "2026-01-01",
                "partner_id": self.partner_a.id,
                "amount": 100.0,
            }
        )
        inv_line = payment.move_id.line_ids.filtered(lambda l: l.balance == 200)
        statement_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "balance": -200.0,
                    "reconciled": True,
                },
                {
                    "account_id": statement_line.journal_id.suspense_account_id.id,
                    "balance": 100.0,
                    "reconciled": False,
                },
            ],
        )
