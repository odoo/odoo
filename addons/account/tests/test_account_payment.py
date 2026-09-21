from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestAccountPayment(AccountTestInvoicingCommon, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency("EUR")

        cls.payment_debit_account_id = cls.inbound_payment_channel.payment_account_id
        cls.payment_credit_account_id = cls.outbound_payment_channel.payment_account_id

        cls.bank_journal_1 = cls.company_data["default_journal_bank"]
        cls.bank_journal_2 = cls.company_data["default_journal_bank"].copy()

        cls.partner_bank_account1 = cls.env["res.partner.bank.account"].create(
            {
                "acc_number": "0123456789",
                "partner_id": cls.partner_a.id,
                "acc_type": "bank",
            }
        )
        cls.partner_bank_account2 = cls.env["res.partner.bank.account"].create(
            {
                "acc_number": "9876543210",
                "partner_id": cls.partner_a.id,
                "acc_type": "bank",
            }
        )
        cls.comp_bank_account1 = cls.env["res.partner.bank.account"].create(
            {
                "acc_number": "985632147",
                "partner_id": cls.env.company.partner_id.id,
                "acc_type": "bank",
                "allow_out_payment": True,
            }
        )
        cls.comp_bank_account2 = cls.env["res.partner.bank.account"].create(
            {
                "acc_number": "741258963",
                "partner_id": cls.env.company.partner_id.id,
                "acc_type": "bank",
                "allow_out_payment": True,
            }
        )

        cls.pay_term_epd = cls.env["account.payment.term"].create(
            [
                {
                    "name": "test",
                    "early_discount": True,
                    "discount_percentage": 10,
                    "discount_days": 10,
                    "line_ids": [
                        Command.create(
                            {
                                "value": "percent",
                                "value_amount": 100,
                                "nb_days": 30,
                            }
                        ),
                    ],
                }
            ]
        )

    def test_payment_move_sync_create_write(self):
        copy_receivable = self.copy_account(
            self.company_data["default_account_receivable"]
        )

        payment = self.env["account.payment"].create(
            {
                "amount": 50.0,
                "payment_type": "inbound",
                "partner_type": "customer",
                "destination_account_id": copy_receivable.id,
            }
        )
        payment.action_post()

        expected_payment_values = {
            "amount": 50.0,
            "payment_type": "inbound",
            "partner_type": "customer",
            "payment_reference": False,
            "is_invoice_reconciled": False,
            "currency_id": self.company_data["currency"].id,
            "partner_id": False,
            "destination_account_id": copy_receivable.id,
            "payment_channel_id": self.inbound_payment_channel.id,
        }
        expected_move_values = {
            "currency_id": self.company_data["currency"].id,
            "partner_id": False,
        }
        expected_liquidity_line = {
            "debit": 50.0,
            "credit": 0.0,
            "amount_currency": 50.0,
            "currency_id": self.company_data["currency"].id,
            "account_id": self.payment_debit_account_id.id,
        }
        expected_counterpart_line = {
            "debit": 0.0,
            "credit": 50.0,
            "amount_currency": -50.0,
            "currency_id": self.company_data["currency"].id,
            "account_id": copy_receivable.id,
        }

        self.assertRecordValues(payment, [expected_payment_values])
        self.assertRecordValues(payment.move_id, [expected_move_values])
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                expected_counterpart_line,
                expected_liquidity_line,
            ],
        )

        payment.move_id.action_cancel()
        self.assertRecordValues(payment, [{"state": "canceled"}])

    def test_payment_move_sync_update_journal_custom_accounts(self):
        outstanding_payment_A = self.inbound_payment_channel.payment_account_id
        outstanding_payment_B = self.inbound_payment_channel.payment_account_id.copy()
        journal_A = self.company_data["default_journal_bank"]
        journal_A.inbound_payment_channel_ids.payment_account_id = outstanding_payment_A
        journal_B = self.company_data["default_journal_bank"].copy()
        journal_B.inbound_payment_channel_ids.payment_account_id = outstanding_payment_B

        pay_form = Form(
            self.env["account.payment"].with_context(
                default_journal_id=self.company_data["default_journal_bank"].id
            )
        )
        pay_form.amount = 50.0
        pay_form.payment_type = "inbound"
        pay_form.partner_id = self.partner_a
        pay_form.journal_id = journal_A
        payment = pay_form.save()
        payment.action_post()

        self.assertRecordValues(
            payment,
            [
                {
                    "amount": 50.0,
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "payment_reference": False,
                    "is_invoice_reconciled": False,
                    "currency_id": self.company_data["currency"].id,
                    "partner_id": self.partner_a.id,
                    "journal_id": journal_A.id,
                }
            ],
        )
        self.assertRecordValues(
            payment.move_id,
            [
                {
                    "currency_id": self.company_data["currency"].id,
                    "partner_id": self.partner_a.id,
                    "journal_id": journal_A.id,
                }
            ],
        )
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                {
                    "debit": 0.0,
                    "credit": 50.0,
                    "amount_currency": -50.0,
                    "currency_id": self.company_data["currency"].id,
                    "account_id": self.company_data["default_account_receivable"].id,
                },
                {
                    "debit": 50.0,
                    "credit": 0.0,
                    "amount_currency": 50.0,
                    "currency_id": self.company_data["currency"].id,
                    "account_id": outstanding_payment_A.id,
                },
            ],
        )

    def test_payment_move_sync_onchange(self):
        pay_form = Form(
            self.env["account.payment"].with_context(
                default_journal_id=self.company_data["default_journal_bank"].id,
                default_partner_type="customer",
            )
        )
        pay_form.amount = 50.0
        pay_form.payment_type = "inbound"
        pay_form.partner_id = self.partner_a
        payment = pay_form.save()
        payment.action_post()

        expected_payment_values = {
            "amount": 50.0,
            "payment_type": "inbound",
            "partner_type": "customer",
            "payment_reference": False,
            "is_invoice_reconciled": False,
            "currency_id": self.company_data["currency"].id,
            "partner_id": self.partner_a.id,
            "destination_account_id": self.partner_a.property_account_receivable_id.id,
            "payment_channel_id": self.inbound_payment_channel.id,
        }
        expected_move_values = {
            "currency_id": self.company_data["currency"].id,
            "partner_id": self.partner_a.id,
        }
        expected_liquidity_line = {
            "debit": 50.0,
            "credit": 0.0,
            "amount_currency": 50.0,
            "currency_id": self.company_data["currency"].id,
            "account_id": self.payment_debit_account_id.id,
        }
        expected_counterpart_line = {
            "debit": 0.0,
            "credit": 50.0,
            "amount_currency": -50.0,
            "currency_id": self.company_data["currency"].id,
            "account_id": self.company_data["default_account_receivable"].id,
        }

        self.assertRecordValues(payment, [expected_payment_values])
        self.assertRecordValues(payment.move_id, [expected_move_values])
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                expected_counterpart_line,
                expected_liquidity_line,
            ],
        )

        payment.action_draft()
        payment.partner_type = "supplier"
        payment.date = "2024-01-01"
        pay_form = Form(payment)
        pay_form.currency_id = self.other_currency
        payment = pay_form.save()
        self.assertRecordValues(
            payment,
            [
                {
                    **expected_payment_values,
                    "partner_type": "supplier",
                    "date": fields.Date.from_string("2024-01-01"),
                    "destination_account_id": self.partner_a.property_account_payable_id.id,
                    "currency_id": self.other_currency.id,
                    "partner_id": self.partner_a.id,
                }
            ],
        )
        self.assertRecordValues(
            payment.move_id,
            [
                {
                    **expected_move_values,
                    "currency_id": self.other_currency.id,
                    "partner_id": self.partner_a.id,
                    "date": fields.Date.from_string("2024-01-01"),
                }
            ],
        )
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                {
                    **expected_counterpart_line,
                    "debit": 0.0,
                    "credit": 25.0,
                    "amount_currency": -50.0,
                    "currency_id": self.other_currency.id,
                    "account_id": self.partner_a.property_account_payable_id.id,
                },
                {
                    **expected_liquidity_line,
                    "debit": 25.0,
                    "credit": 0.0,
                    "amount_currency": 50.0,
                    "currency_id": self.other_currency.id,
                },
            ],
        )

    def test_payment_journal_onchange(self):
        pay_form = Form(
            self.env["account.payment"].with_context(
                default_journal_id=self.company_data["default_journal_bank"].id,
                default_partner_type="customer",
            )
        )
        pay_form.amount = 50.0
        pay_form.payment_type = "inbound"
        pay_form.partner_id = self.partner_a
        payment = pay_form.save()

        with self.assertRaises(AssertionError):
            pay_form.journal_id = self.env["account.journal"]
            payment = pay_form.save()

        self.assertRecordValues(
            payment,
            [
                {
                    "amount": 50.0,
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "payment_reference": False,
                    "is_invoice_reconciled": False,
                    "currency_id": self.company_data["currency"].id,
                    "partner_id": self.partner_a.id,
                    "destination_account_id": self.partner_a.property_account_receivable_id.id,
                    "payment_channel_id": self.inbound_payment_channel.id,
                    "journal_id": self.company_data["default_journal_bank"].id,
                }
            ],
        )

    def test_attachments_send_multiple(self):
        payments = self.env["account.payment"].create(
            [
                {
                    "amount": 100.0,
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": p.id,
                }
                for p in (self.partner_a, self.partner_b)
            ]
        )

        form = Form(
            self.env["mail.compose.message"].with_context(
                {
                    "mailing_document_based": True,
                    "mail_post_autofollow": True,
                    "default_composition_mode": "mass_mail",
                    "default_template_id": self.env.ref(
                        "account.mail_template_data_payment_receipt"
                    ),
                    "default_email_layout_xmlid": "mail.mail_notification_light",
                    "default_model": "account.payment",
                    "default_res_ids": payments.ids,
                }
            )
        )
        saved_form = form.save()
        with self.mock_mail_gateway():
            saved_form._action_send_mail()

        for p in payments:
            self.assertTrue(p._get_mail_thread_data_attachments()[p.id])

    def test_compute_currency_id(self):
        self.company_data["default_journal_bank"].currency_id = self.other_currency
        self.company_data[
            "default_journal_bank"
        ].inbound_payment_channel_ids.payment_account_id = (
            self.inbound_payment_channel.payment_account_id
        )

        payment = self.env["account.payment"].create(
            {
                "amount": 50.0,
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        payment.action_post()

        self.assertRecordValues(
            payment,
            [
                {
                    "currency_id": self.other_currency.id,
                }
            ],
        )
        self.assertRecordValues(
            payment.move_id,
            [
                {
                    "currency_id": self.other_currency.id,
                }
            ],
        )
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                {
                    "debit": 0.0,
                    "credit": 25.0,
                    "amount_currency": -50.0,
                    "currency_id": self.other_currency.id,
                },
                {
                    "debit": 25.0,
                    "credit": 0.0,
                    "amount_currency": 50.0,
                    "currency_id": self.other_currency.id,
                },
            ],
        )

    def test_reconciliation_payment_states(self):
        payment = self.env["account.payment"].create(
            {
                "amount": 50.0,
                "payment_type": "inbound",
                "partner_type": "customer",
                "destination_account_id": self.company_data[
                    "default_account_receivable"
                ].id,
            }
        )
        payment.action_post()
        liquidity_lines, counterpart_lines, _writeoff_lines = payment._seek_for_lines()

        self.assertRecordValues(
            payment,
            [
                {
                    "is_invoice_reconciled": False,
                    "is_bank_matched": False,
                }
            ],
        )

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "50 to pay",
                            "price_unit": 50.0,
                            "quantity": 1,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        },
                    )
                ],
            }
        )
        invoice.action_post()

        (
            counterpart_lines
            + invoice.line_ids.filtered(
                lambda line: line.account_type == "asset_receivable"
            )
        ).reconcile()

        self.assertRecordValues(
            payment,
            [
                {
                    "is_invoice_reconciled": True,
                    "is_bank_matched": False,
                }
            ],
        )

        statement_line = self.env["account.bank.statement.line"].create(
            {
                "payment_ref": "50 to pay",
                "journal_id": self.company_data["default_journal_bank"].id,
                "partner_id": self.partner_a.id,
                "amount": 50.0,
            }
        )

        _st_liquidity_lines, st_suspense_lines, _st_other_lines = (
            statement_line.with_context(
                skip_account_move_synchronization=True
            )._seek_for_lines()
        )
        st_suspense_lines.account_id = liquidity_lines.account_id
        (st_suspense_lines + liquidity_lines).reconcile()

        self.assertRecordValues(
            payment,
            [
                {
                    "is_invoice_reconciled": True,
                    "is_bank_matched": True,
                }
            ],
        )

    def test_invoice_payment_state_follows_counterpart_payment_matching(self):
        def in_payment(self):
            return "in_payment"

        with patch.object(
            self.env.registry["account.move"],
            "_get_invoice_in_payment_state",
            in_payment,
        ):
            invoice = self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [
                        Command.create({"product_id": self.product_a.id})
                    ],
                }
            )
            invoice.action_post()

            payment = (
                self.env["account.payment.register"]
                .with_context(active_model="account.move", active_ids=invoice.ids)
                .create({})
                ._create_payments()
            )
            self.assertFalse(payment.is_bank_matched)
            self.assertEqual(invoice.payment_state, "in_payment")

            liquidity_lines, _counterpart, _writeoff = payment._seek_for_lines()
            statement_line = self.env["account.bank.statement.line"].create(
                {
                    "payment_ref": "matching the payment",
                    "journal_id": self.company_data["default_journal_bank"].id,
                    "partner_id": self.partner_a.id,
                    "amount": payment.amount,
                }
            )
            _st_liquidity, st_suspense_lines, _st_other = statement_line.with_context(
                skip_account_move_synchronization=True
            )._seek_for_lines()
            st_suspense_lines.account_id = liquidity_lines.account_id
            (st_suspense_lines + liquidity_lines).reconcile()

            self.assertTrue(payment.is_bank_matched)
            self.assertEqual(invoice.payment_state, "paid")

    def test_reconciliation_payment_states_reverse_payment_move(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [Command.create({"product_id": self.product_a.id})],
            }
        )
        invoice.action_post()

        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({})
            ._create_payments()
        )

        self.assertTrue(invoice.payment_state in ("paid", "in_payment"))
        self.assertRecordValues(payment, [{"reconciled_invoice_ids": invoice.ids}])

        reversal_wizard = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=payment.move_id.ids)
            .create({"reason": "oopsie", "journal_id": payment.journal_id.id})
        )
        reversal_wizard.refund_moves()
        self.assertRecordValues(invoice, [{"payment_state": "not_paid"}])
        self.assertRecordValues(payment.move_id.line_ids, [{"reconciled": True}] * 2)

    def test_payment_without_default_company_account(self):
        bank_journal = self.company_data["default_journal_bank"]

        bank_journal.outbound_payment_channel_ids.payment_account_id = (
            self.outbound_payment_channel.payment_account_id.copy()
        )
        bank_journal.inbound_payment_channel_ids.payment_account_id = (
            self.inbound_payment_channel.payment_account_id.copy()
        )

        payment = self.env["account.payment"].create(
            {
                "amount": 5.0,
                "payment_type": "inbound",
                "partner_type": "customer",
                "journal_id": bank_journal.id,
            }
        )
        self.assertRecordValues(
            payment,
            [
                {
                    "amount": 5.0,
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "payment_reference": False,
                    "is_invoice_reconciled": False,
                    "currency_id": self.company_data["currency"].id,
                    "partner_id": False,
                    "payment_channel_id": self.inbound_payment_channel.id,
                }
            ],
        )

        payment.payment_type = "outbound"
        self.assertRecordValues(
            payment,
            [
                {
                    "amount": 5.0,
                    "payment_type": "outbound",
                    "partner_type": "customer",
                    "payment_reference": False,
                    "is_invoice_reconciled": False,
                    "currency_id": self.company_data["currency"].id,
                    "partner_id": False,
                    "payment_channel_id": self.outbound_payment_channel.id,
                }
            ],
        )

    def test_suggested_default_partner_bank(self):
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.bank_journal_1.id,
                "amount": 50.0,
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.partner_a.id,
            }
        )
        self.assertRecordValues(
            payment,
            [
                {
                    "available_partner_bank_ids": self.partner_a.bank_ids.ids,
                    "partner_bank_id": self.partner_bank_account1.id,
                }
            ],
        )

        payment.payment_type = "inbound"
        self.assertRecordValues(
            payment,
            [
                {
                    "available_partner_bank_ids": [],
                    "partner_bank_id": False,
                }
            ],
        )

        self.bank_journal_2.bank_account_id = self.comp_bank_account2
        payment.name = False
        payment.journal_id = self.bank_journal_2
        self.assertRecordValues(
            payment,
            [
                {
                    "available_partner_bank_ids": self.comp_bank_account2.ids,
                    "partner_bank_id": self.comp_bank_account2.id,
                }
            ],
        )

    def test_reconciliation_with_old_oustanding_account(self):
        outstanding_account_2 = self.inbound_payment_channel.payment_account_id.copy()

        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "journal_id": self.company_data["default_journal_bank"].id,
                "amount": 1150,
            }
        )
        payment.action_post()

        self.company_data[
            "default_journal_bank"
        ].inbound_payment_channel_ids.payment_account_id = outstanding_account_2
        invoice = self.init_invoice(
            "out_invoice", post=True, amounts=[1000.0], taxes=self.env["account.tax"]
        )

        credit_line = payment.move_id.line_ids.filtered(
            lambda l: (
                l.credit
                and l.account_id == self.company_data["default_account_receivable"]
            )
        )

        invoice.js_add_outstanding_line(credit_line.id)
        self.assertTrue(
            invoice.payment_state in ("in_payment", "paid"), "Invoice should be paid"
        )
        invoice.action_draft()
        invoice.line_ids.remove_move_reconcile()
        self.assertTrue(
            invoice.payment_state == "not_paid", "Invoice should'nt be paid anymore"
        )
        self.assertTrue(invoice.state == "draft", "Invoice should be draft")

    def test_journal_onchange(self):
        context = {
            "payment_type": "inbound",
            "partner_type": "customer",
        }
        with Form(self.env["account.payment"].with_context(context)) as payment:
            default_journal = payment.journal_id
            self.assertTrue(default_journal)
            self.assertEqual(
                payment.payment_channel_id.journal_id.id, default_journal.id
            )

            other_journal = (
                self.bank_journal_2
                if default_journal != self.bank_journal_2
                else self.bank_journal_1
            )
            payment.journal_id = other_journal
            self.assertEqual(payment.payment_channel_id.journal_id.id, other_journal.id)

            payment.journal_id = default_journal
            self.assertEqual(
                payment.payment_channel_id.journal_id.id, default_journal.id
            )

    def test_journal_change_and_change_names(self):
        initial_journal = self.company_data["default_journal_bank"]
        new_journal = self.company_data["default_journal_cash"]

        payment_channel = initial_journal.inbound_payment_channel_ids[0]

        new_journal.inbound_payment_channel_ids[
            0
        ].payment_account_id = self.payment_debit_account_id

        payment = self.env["account.payment"].create(
            {
                "amount": 50.0,
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "journal_id": initial_journal.id,
                "payment_channel_id": payment_channel.id,
            }
        )
        payment.action_post()

        payment.action_draft()
        payment.journal_id = new_journal
        payment.payment_channel_id = new_journal.inbound_payment_channel_ids[0]
        payment.action_post()

        self.assertRegex(payment.move_id.name, rf"^P{new_journal.code}/")

    def test_payments_copy_data(self):
        payment_1, payment_2 = self.env["account.payment"].create(
            [
                {
                    "partner_id": self.partner_a.id,
                    "amount": 50,
                },
                {
                    "partner_id": self.partner_b.id,
                    "amount": 100,
                },
            ]
        )
        duplicate_payment_1, duplicate_payment_2 = (payment_1 + payment_2).copy()

        self.assertEqual(duplicate_payment_1.partner_id, payment_1.partner_id)
        self.assertEqual(duplicate_payment_2.partner_id, payment_2.partner_id)

        self.assertEqual(duplicate_payment_1.amount, payment_1.amount)
        self.assertEqual(duplicate_payment_2.amount, payment_2.amount)

    def test_payments_epd_eligible_on_move_with_payment(self):
        invoice1 = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "date": "2024-01-01",
                    "invoice_payment_term_id": self.pay_term_epd.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "test",
                                "quantity": 1,
                                "price_unit": 1000,
                            }
                        )
                    ],
                }
            ]
        )
        invoice1.action_post()
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice1.ids
        ).create({})._create_payments()
        self.assertFalse(
            invoice1._is_eligible_for_early_payment_discount(
                invoice1.currency_id, invoice1.invoice_date
            )
        )
        self.company_data[
            "default_journal_bank"
        ].inbound_payment_channel_ids.payment_account_id = self.env["account.account"]
        invoice2 = invoice1.copy()
        invoice2.action_post()
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice2.ids
        ).create({})._create_payments()

        is_accounting_installed = (
            invoice1._get_invoice_in_payment_state() == "in_payment"
        )

        self.assertEqual(
            invoice2._is_eligible_for_early_payment_discount(
                invoice2.currency_id, invoice2.invoice_date
            ),
            is_accounting_installed,
        )

    def test_payments_invoice_payment_state_without_outstanding_accounts(self):
        def register_payment_and_assert_state(move, amount, is_community):
            def patched_get_invoice_in_payment_state(self):
                return "paid" if is_community else "in_payment"

            with patch.object(
                self.env.registry["account.move"],
                "_get_invoice_in_payment_state",
                patched_get_invoice_in_payment_state,
            ):
                payment = (
                    self.env["account.payment.register"]
                    .with_context(active_model="account.move", active_ids=move.ids)
                    .create({"amount": amount})
                    ._create_payments()
                )

                self.assertEqual(
                    payment.state, "paid" if is_community else "in_process"
                )

        self.company_data[
            "default_journal_bank"
        ].inbound_payment_channel_ids.payment_account_id = self.env["account.account"]

        invoice_1 = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "date": "2024-01-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "test",
                                "quantity": 1,
                                "price_unit": 100.0,
                            }
                        )
                    ],
                }
            ]
        )
        invoice_1.action_post()
        register_payment_and_assert_state(invoice_1, 100.0, is_community=True)
        self.assertTrue(invoice_1.reconciled_payment_ids.move_id)

        invoice_2 = invoice_1.copy()
        invoice_2.action_post()
        register_payment_and_assert_state(invoice_2, 100.0, is_community=False)
        self.assertFalse(invoice_2.reconciled_payment_ids.move_id)

    def test_payment_confirmation_with_bank_outstanding_account(self):
        bank_journal = self.company_data["default_journal_bank"]
        outstanding_account = bank_journal.default_account_id
        bank_journal.inbound_payment_channel_ids.payment_account_id = (
            outstanding_account
        )
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "journal_id": bank_journal.id,
                "amount": 2629,
            }
        )
        payment.action_post()
        self.assertEqual(payment.state, "paid")

    def test_payment_memo_account_move_ref_inverse(self):
        bank_journal = self.company_data["default_journal_bank"]
        bank_journal.inbound_payment_channel_ids.payment_account_id = (
            self.inbound_payment_channel.payment_account_id
        )
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "journal_id": bank_journal.id,
                "amount": 2629,
                "memo": "Test Memo",
            }
        )
        payment.action_post()
        payment.write({"memo": "Updated Memo"})

        self.assertEqual(payment.move_id.ref, payment.memo)

    def test_mandatory_entry_survives_an_ordinary_edit(self):
        journal = self.company_data["default_journal_bank"]
        (
            journal.inbound_payment_channel_ids | journal.outbound_payment_channel_ids
        ).payment_account_id = False
        payment_model = self.env["account.payment"].with_context(
            force_payment_move=True
        )
        vals = {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": self.partner_a.id,
            "journal_id": self.company_data["default_journal_bank"].id,
            "amount": 100.0,
        }
        edits = [
            ("no edit", {}),
            ("payment_type", {"payment_type": "outbound"}),
            ("journal_id, same value", {"journal_id": vals["journal_id"]}),
            ("partner_type", {"partner_type": "supplier"}),
        ]
        for label, edit in edits:
            with self.subTest(label):
                payment = payment_model.create(dict(vals))
                self.assertTrue(
                    payment.outstanding_account_id,
                    "the compute owes a mandatory entry an outstanding account",
                )
                payment.write(edit)
                self.assertTrue(
                    payment.outstanding_account_id,
                    f"{label} cleared the outstanding account",
                )
                payment.action_post()
                self.assertTrue(
                    payment.move_id, f"{label} left the payment with no entry"
                )
                self.assertTrue(
                    payment.move_id.line_ids,
                    f"{label} left the payment with an empty entry",
                )

    def test_mandatory_entry_follows_the_payment_type(self):
        journal = self.company_data["default_journal_bank"]
        (
            journal.inbound_payment_channel_ids | journal.outbound_payment_channel_ids
        ).payment_account_id = False
        payment = (
            self.env["account.payment"]
            .with_context(force_payment_move=True)
            .create(
                {
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "partner_id": self.partner_a.id,
                    "journal_id": journal.id,
                    "amount": 100.0,
                }
            )
        )
        inbound_account = payment.outstanding_account_id
        payment.write({"payment_type": "outbound"})
        self.assertTrue(payment.outstanding_account_id)
        self.assertNotEqual(
            payment.outstanding_account_id,
            inbound_account,
            "an outbound payment settles through the credit account",
        )

    def test_reconciled_invoices_type_counts_distinct_types(self):
        refunds = self.env["account.move"]
        for amount in (30.0, 31.0, 32.0):
            refunds |= self.init_invoice(
                "out_refund", post=True, amounts=[amount], taxes=[]
            )
        for count in (1, 2, 3):
            with self.subTest(credit_notes=count):
                payment = self.env["account.payment"].create(
                    {
                        "payment_type": "outbound",
                        "partner_type": "customer",
                        "partner_id": self.partner_a.id,
                        "journal_id": self.company_data["default_journal_bank"].id,
                        "amount": 50.0,
                        "invoice_ids": [Command.set(refunds[:count].ids)],
                    }
                )
                self.assertEqual(payment.reconciled_invoices_type, "credit_note")

    def test_force_balance_refuses_to_be_discarded(self):
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "journal_id": self.company_data["default_journal_bank"].id,
                "amount": 100.0,
            }
        )
        line_vals = payment._prepare_move_lines_per_type(force_balance=999.0)
        self.assertEqual(line_vals["liquidity_lines"][0]["balance"], 999.0)
        with self.assertRaises(ValueError):
            payment._prepare_move_lines_per_type(
                write_off_line_vals=[
                    {
                        "name": "write-off",
                        "account_id": payment.destination_account_id.id,
                        "partner_id": self.partner_a.id,
                        "currency_id": payment.currency_id.id,
                        "amount_currency": -10.0,
                        "balance": -10.0,
                    }
                ],
                force_balance=999.0,
            )

    def test_payment_state_with_unreconciliable_outstanding_account(self):
        unreconciliable_account = self.env["account.account"].create(
            {
                "code": "209.01.01",
                "name": "Bank Account",
                "account_type": "asset_cash",
                "reconcile": False,
            }
        )
        self.company_data[
            "default_journal_bank"
        ].outbound_payment_channel_ids.payment_account_id = unreconciliable_account
        invoice = self.init_invoice(move_type="out_invoice", amounts=[10], post=True)

        payment = (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=invoice.ids,
            )
            .create(
                {
                    "payment_channel_id": self.company_data["default_journal_bank"]
                    .outbound_payment_channel_ids[0]
                    .id,
                }
            )
            ._create_payments()
        )

        self.assertEqual(payment.state, "paid")

    def test_invoice_paid_hook_called_in_various_scenarios(self):
        def register_payment(invoice, payment_channel, amount=None):
            return (
                self.env["account.payment.register"]
                .with_context(active_model="account.move", active_ids=invoice.ids)
                .create(
                    {
                        **({"amount": amount} if amount is not None else {}),
                        "payment_channel_id": payment_channel.id,
                    }
                )
                ._create_payments()
            )

        def create_statement_line_and_reconcile(amount, payment=None, invoice=None):
            statement_line = self.env["account.bank.statement.line"].create(
                {
                    "payment_ref": (payment.name if payment else invoice.name),
                    "journal_id": self.company_data["default_journal_bank"].id,
                    "partner_id": self.partner_a.id,
                    "amount": amount,
                }
            )
            _st_liquidity_lines, st_suspense_lines, _ = statement_line._seek_for_lines()
            if payment:
                liquidity_lines, _, _ = payment._seek_for_lines()
            else:
                liquidity_lines = invoice.line_ids.filtered(
                    lambda line: line.account_type == "asset_receivable"
                )
            st_suspense_lines.account_id = liquidity_lines.account_id
            (st_suspense_lines + liquidity_lines).reconcile()

        @contextmanager
        def assert_paid_hook_call(subtest_msg):
            with (
                self.subTest(subtest_msg),
                patch.object(
                    self.env.registry["account.move"],
                    "_invoice_paid_hook",
                    autospec=True,
                ) as mock_hook,
            ):
                yield mock_hook
                valid_calls = [
                    call for call in mock_hook.call_args_list if call.args[0]
                ]
                self.assertEqual(
                    len(valid_calls), 1, "invoice paid hook should be called once"
                )

        journal = self.company_data["default_journal_bank"]
        payment_method = journal.available_payment_method_ids.filtered(
            lambda pm: pm.payment_type == "inbound" and pm.code == "manual"
        )
        line_with_outstanding = self.env["account.payment.channel"].create(
            {
                "payment_method_id": payment_method.id,
                "journal_id": journal.id,
                "payment_account_id": self.payment_debit_account_id.id,
            }
        )
        line_without_outstanding = self.env["account.payment.channel"].create(
            {
                "payment_method_id": payment_method.id,
                "journal_id": journal.id,
            }
        )

        with assert_paid_hook_call("with oustanding"):
            invoice = self.init_invoice(
                "out_invoice", post=True, amounts=[1000.0], taxes=[]
            )
            payment = register_payment(invoice, line_with_outstanding)
            create_statement_line_and_reconcile(
                payment=payment, amount=invoice.amount_total
            )

        with assert_paid_hook_call("without oustanding"):
            if self.env["account.move"]._get_invoice_in_payment_state() != "in_payment":
                self.skipTest("Accounting not installed")
            invoice = self.init_invoice(
                "out_invoice", post=True, amounts=[1000.0], taxes=[]
            )
            payment = register_payment(invoice, line_without_outstanding)
            create_statement_line_and_reconcile(
                invoice=invoice, amount=invoice.amount_total
            )

        with assert_paid_hook_call("without payment"):
            invoice = self.init_invoice(
                "out_invoice", post=True, amounts=[1000.0], taxes=[]
            )
            create_statement_line_and_reconcile(
                invoice=invoice, amount=invoice.amount_total
            )

        with assert_paid_hook_call("with mixed oustanding"):
            if self.env["account.move"]._get_invoice_in_payment_state() != "in_payment":
                self.skipTest("Accounting not installed")
            invoice = self.init_invoice(
                "out_invoice", post=True, amounts=[1000.0], taxes=[]
            )
            payment = register_payment(
                invoice, line_with_outstanding, invoice.amount_total / 2
            )
            create_statement_line_and_reconcile(
                payment=payment, amount=invoice.amount_total / 2
            )
            payment = register_payment(
                invoice, line_without_outstanding, invoice.amount_total / 2
            )
            create_statement_line_and_reconcile(
                invoice=invoice, amount=invoice.amount_total / 2
            )

    def test_resequence_change_payment_name(self):
        invoice = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "date": "2024-01-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "test",
                                "quantity": 1,
                                "price_unit": 100.0,
                            }
                        )
                    ],
                }
            ]
        )
        invoice.action_post()

        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({})
            ._create_payments()
        )

        payment.action_post()

        year = fields.Date.today().year
        wizard = (
            self.env["account.resequence.wizard"]
            .with_context(
                {
                    "active_ids": payment.move_id.ids,
                    "active_model": "account.move",
                }
            )
            .create(
                {
                    "first_name": f"PBNK1/{year}/00002",
                }
            )
        )
        wizard.resequence()

        self.assertEqual(payment.move_id.name, f"PBNK1/{year}/00002")
        self.assertEqual(payment.name, f"PBNK1/{year}/00002")

    def test_vendor_payment_save_user_selected_journal_id(self):
        journal_bank = self.env["account.journal"].search([("name", "=", "Bank")])
        journal_cash = self.env["account.journal"].search([("name", "=", "Cash")])

        self.partner.property_outbound_payment_channel_id = (
            journal_cash.outbound_payment_channel_ids
        )
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_id": self.partner.id,
                "journal_id": journal_cash.id,
            }
        )
        self.assertEqual(payment.journal_id, journal_cash)
        payment.journal_id = journal_bank

        self.assertEqual(payment.payment_channel_id.journal_id, payment.journal_id)
        self.assertEqual(payment.journal_id, journal_bank)

    def test_empty_string_payment_method(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [Command.create({"product_id": self.product_a.id})],
            }
        )
        invoice.action_post()

        journal = self.company_data["default_journal_bank"]
        payment_channel = journal.inbound_payment_channel_ids.filtered(
            lambda pm: pm.code == "manual"
        )
        payment_channel.write(
            {
                "name": False,
                "payment_account_id": self.payment_debit_account_id.id,
            }
        )

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create({"payment_channel_id": payment_channel.id})._create_payments()
        self.assertEqual(invoice.state, "posted")

    def test_payment_amount_without_move(self):
        bank_journal_2 = self.company_data["default_journal_bank"].copy()

        payment = self.env["account.payment"].create(
            {
                "amount": 100,
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.partner_a.id,
                "currency_id": self.other_currency.id,
                "journal_id": bank_journal_2.id,
            }
        )

        payment.action_post()

        self.assertRecordValues(
            payment,
            [
                {
                    "amount": 100,
                    "amount_signed": -100,
                    "amount_company_currency_signed": -50,
                }
            ],
        )

    def test_payment_state_computation(self):
        def create_invoice(post=False, kwargs=None):
            move = self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [
                        Command.create({"product_id": self.product_a.id})
                    ],
                }
            )
            if post:
                move.action_post()
            if kwargs is not None:
                move.update({**kwargs})
            return move

        for post, payment_state, expected in [
            (False, "not_paid", "draft"),
            (False, "partial", "partial"),
            (False, "in_payment", "in_payment"),
            (False, "paid", "paid"),
            (True, "partial", "partial"),
            (True, "in_payment", "in_payment"),
            (True, "paid", "paid"),
            (True, "reversed", "reversed"),
        ]:
            invoice = create_invoice(post=post, kwargs={"payment_state": payment_state})
            self.assertEqual(invoice.display_state, expected)

        for is_move_sent, expected in [
            (True, "sent"),
            (False, "posted"),
        ]:
            invoice = create_invoice(post=True, kwargs={"is_move_sent": is_move_sent})
            self.assertEqual(invoice.display_state, expected)

    def test_payment_move_with_multiple_liquidity_lines(self):
        payment = self.env["account.payment"].create(
            {
                "amount": 150.0,
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        payment.action_post()
        move = payment.move_id
        move.action_draft()
        liquidity_lines = payment._seek_for_lines()[0]
        move.write(
            {
                "line_ids": [
                    Command.update(liquidity_lines.id, {"amount_currency": 100}),
                    Command.create(
                        {
                            "account_id": liquidity_lines.account_id.id,
                            "balance": 50.0,
                            "amount_currency": 50.0,
                            "currency_id": payment.currency_id.id,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        payment.action_draft()
        with self.assertRaises(UserError):
            payment.amount = 300.0
