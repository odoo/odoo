import base64
import re

from odoo import Command, fields
from odoo.tests import tagged

from .common_reconcile import TestBankRecWidgetCommon


@tagged("post_install", "-at_install")
class TestAccountBankStatement(TestBankRecWidgetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()
        cls.account_revenue_1 = cls.company_data["default_account_revenue"]
        cls.account_revenue_1.reconcile = True

        cls.early_payment_term = cls.env["account.payment.term"].create(
            {
                "name": "Early_payment_term",
                "company_id": cls.company_data["company"].id,
                "discount_percentage": 10,
                "discount_days": 10,
                "early_discount": True,
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100,
                            "nb_days": 20,
                        }
                    ),
                ],
            }
        )

        cls.default_tax = cls.env["account.tax"].create(
            {
                "name": "default_tax",
                "amount_type": "fixed",
                "amount": 10.0,
            }
        )
        cls.default_tax_account = cls.env["account.account"].create(
            {
                "name": "account with default tax",
                "code": "101010",
                "tax_ids": [Command.set(cls.default_tax.ids)],
            }
        )

    def _create_and_post_payment(self, amount=100, memo=None, post=True, **kwargs):
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "payment_method_id": self.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": amount,
                "journal_id": self.company_data["default_journal_bank"].id,
                "memo": memo,
                **kwargs,
            }
        )
        if post:
            payment.action_post()
        return payment

    def test_set_line_bank_statement_line_multiple_move_lines(self):
        statement_line = self._create_st_line(amount=150, update_create_date=False)
        self.assertEqual(len(statement_line.move_id.line_ids), 2)

        move_line_1 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 100.0}]
        )
        move_line_2 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 50.0}]
        )

        statement_line.set_line_bank_statement_line([move_line_1.id, move_line_2.id])

        self.assertEqual(len(statement_line.move_id.line_ids), 3)
        self.assertNotEqual(
            statement_line.move_id.line_ids[-1].account_id,
            statement_line.journal_id.suspense_account_id,
        )

    def test_set_line_bank_statement_line_with_open_balance(self):
        statement_line = self._create_st_line(amount=200, update_create_date=False)
        self.assertEqual(len(statement_line.move_id.line_ids), 2)

        move_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 150.0}]
        )
        statement_line.set_line_bank_statement_line(move_line.id)

        self.assertRecordValues(
            statement_line.move_id.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "debit": 200.0,
                    "credit": 0.0,
                },
                {
                    "account_id": move_line.account_id.id,
                    "debit": 0.0,
                    "credit": 150.0,
                },
                {
                    "account_id": statement_line.journal_id.suspense_account_id.id,
                    "debit": 0.0,
                    "credit": 50.0,
                },
            ],
        )

    def test_set_line_bank_statement_line_excess_payment(self):
        statement_line = self._create_st_line(amount=200, update_create_date=False)
        self.assertEqual(len(statement_line.move_id.line_ids), 2)

        move_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 250.0}]
        )

        statement_line.set_line_bank_statement_line(move_line.id)

        self.assertRecordValues(
            statement_line.move_id.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "debit": 200.0,
                    "credit": 0.0,
                },
                {
                    "account_id": move_line.account_id.id,
                    "debit": 0.0,
                    "credit": 200.0,
                },
            ],
        )

        suspense_line = statement_line.move_id.line_ids.filtered(
            lambda line: (
                line.account_id == statement_line.journal_id.suspense_account_id
            )
        )
        self.assertEqual(len(suspense_line), 0)

    def test_set_line_bank_statement_line_excess_payment_negative(self):
        statement_line = self._create_st_line(amount=-200, update_create_date=False)
        self.assertEqual(len(statement_line.move_id.line_ids), 2)

        move_line = self._create_invoice_line(
            "in_invoice", invoice_line_ids=[{"price_unit": 250.0}]
        )

        statement_line.set_line_bank_statement_line(move_line.id)

        self.assertRecordValues(
            statement_line.move_id.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "debit": 0.0,
                    "credit": 200.0,
                },
                {
                    "account_id": move_line.account_id.id,
                    "debit": 200.0,
                    "credit": 0.0,
                },
            ],
        )

        suspense_line = statement_line.move_id.line_ids.filtered(
            lambda line: (
                line.account_id == statement_line.journal_id.suspense_account_id
            )
        )
        self.assertEqual(len(suspense_line), 0)

    def test_remove_reconciled_line_with_suspense(self):
        statement_line = self._create_st_line(amount=200, update_create_date=False)

        move_line_1 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 150.0}]
        )
        move_line_2 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 50.0}]
        )
        statement_line.set_line_bank_statement_line([move_line_1.id, move_line_2.id])
        self.assertRecordValues(
            statement_line.move_id.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "debit": 200.0,
                    "credit": 0.0,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "debit": 0.0,
                    "credit": 150.0,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "debit": 0.0,
                    "credit": 50.0,
                },
            ],
        )

        _liquidity_lines, _suspense_lines, other_lines = (
            statement_line._seek_for_lines()
        )
        for id in other_lines.ids:
            statement_line.remove_reconciled_line(id)
        self.assertRecordValues(
            statement_line.move_id.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "debit": 200.0,
                    "credit": 0.0,
                },
                {
                    "account_id": statement_line.journal_id.suspense_account_id.id,
                    "debit": 0.0,
                    "credit": 200.0,
                },
            ],
        )

    def test_reconciliation_base_case_invoice(self):
        st_line = self._create_st_line(1000.0, update_create_date=False)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 1000.0, "tax_ids": []}],
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconciliation_base_case_bill(self):
        st_line = self._create_st_line(-1000.0, update_create_date=False)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
            ],
        )
        inv_line = self._create_invoice_line(
            "in_invoice",
            invoice_line_ids=[{"price_unit": 1000.0, "tax_ids": []}],
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_payable_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconciliation_with_unique_label_memo_match(self):
        payment = self._create_and_post_payment(amount=100, memo="pay_AretqwwXerereE")
        statement_line = self._create_st_line(
            amount=100, payment_ref="pay_AretqwwXerereE", update_create_date=False
        )
        statement_line._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": payment.outstanding_account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconciliation_with_unique_label_memo_match_and_negative_amounts(self):
        payment = self._create_and_post_payment(amount=100, memo="pay_AretqwwXerereE")
        statement_line = self._create_st_line(
            amount=-100, payment_ref="pay_AretqwwXerereE", update_create_date=False
        )
        statement_line._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": False,
                },
                {
                    "account_id": payment.destination_account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconciliation_with_unique_label_memo_match_and_other_currency_on_payment(
        self,
    ):
        payment = self._create_and_post_payment(
            amount=200, memo="pay_AretqwwXerereE", currency_id=self.other_currency.id
        )
        statement_line = self._create_st_line(
            amount=100, payment_ref="pay_AretqwwXerereE", update_create_date=False
        )
        statement_line._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": payment.outstanding_account_id.id,
                    "amount_currency": -200.0,
                    "currency_id": self.other_currency.id,
                    "balance": -100.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconciliation_with_unique_label_memo_match_and_other_currency_on_payment_and_st_line(
        self,
    ):
        payment = self._create_and_post_payment(
            amount=200, memo="pay_AretqwwXerereE", currency_id=self.other_currency.id
        )
        statement_line = self._create_st_line(
            amount=100,
            amount_currency=200,
            payment_ref="pay_AretqwwXerereE",
            update_create_date=False,
            foreign_currency_id=self.other_currency.id,
        )
        statement_line._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": payment.outstanding_account_id.id,
                    "amount_currency": -200.0,
                    "currency_id": self.other_currency.id,
                    "balance": -100.0,
                    "reconciled": True,
                },
            ],
        )

    def test_multiple_reconcile_with_same_payment(self):
        payment = self._create_and_post_payment(amount=200, memo="pay_AretqwwXerereE")
        statement_line_1 = self._create_st_line(
            amount=100, payment_ref="pay_AretqwwXerereE", update_create_date=False
        )
        statement_line_1._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line_1.line_ids,
            [
                {
                    "account_id": statement_line_1.journal_id.default_account_id.id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": payment.outstanding_account_id.id,
                    "balance": -100.0,
                    "reconciled": True,
                },
            ],
        )
        self.assertEqual(payment.state, "in_process")
        statement_line_2 = self._create_st_line(
            amount=100, payment_ref="pay_AretqwwXerereE", update_create_date=False
        )
        statement_line_2._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line_2.line_ids,
            [
                {
                    "account_id": statement_line_2.journal_id.default_account_id.id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": payment.outstanding_account_id.id,
                    "balance": -100.0,
                    "reconciled": True,
                },
            ],
        )
        self.assertEqual(payment.state, "paid")

    def test_multiple_reconcile_with_foreign_currency(self):
        payment = self._create_and_post_payment(
            amount=400, memo="pay_AretqwwXerereE", currency_id=self.other_currency.id
        )
        statement_line_1 = self._create_st_line(
            amount=200, payment_ref="pay_AretqwwXerereE", update_create_date=False
        )
        statement_line_1._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line_1.line_ids,
            [
                {
                    "account_id": statement_line_1.journal_id.default_account_id.id,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": payment.outstanding_account_id.id,
                    "balance": -200.0,
                    "reconciled": True,
                },
            ],
        )

        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-01",
            invoice_line_ids=[{"price_unit": 1000.0}],
        )
        statement_line_2 = self._create_st_line(
            amount=1000, payment_ref=inv_line.name, update_create_date=False
        )
        statement_line_2._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line_2.line_ids,
            [
                {
                    "account_id": statement_line_2.journal_id.default_account_id.id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "balance": -1000.0,
                    "reconciled": True,
                },
            ],
        )
        foreign_inv_line = self._create_invoice_line(
            "out_invoice",
            currency_id=self.other_currency.id,
            invoice_date="2017-01-01",
            invoice_line_ids=[{"price_unit": 2000.0}],
        )
        statement_line_3 = self._create_st_line(
            amount=1000, payment_ref=foreign_inv_line.name, update_create_date=False
        )
        statement_line_3._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line_3.line_ids,
            [
                {
                    "account_id": statement_line_2.journal_id.default_account_id.id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": statement_line_2.journal_id.suspense_account_id.id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )

    def test_unreconciliation_base_case_invoice(self):
        st_line = self._create_st_line(1000.0, update_create_date=False)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 1000.0, "tax_ids": []}],
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": True,
                },
            ],
        )
        line_to_remove = st_line.line_ids[-1]
        line_to_remove_source = line_to_remove.reconciled_lines_ids
        self.assertTrue(line_to_remove.matched_debit_ids)
        self.assertTrue(line_to_remove_source.matched_credit_ids)
        st_line.remove_reconciled_line(st_line.line_ids[-1].id)
        self.assertFalse(line_to_remove_source.matched_credit_ids)

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )

    def test_unreconciliation_base_case_bill(self):
        st_line = self._create_st_line(-1000.0, update_create_date=False)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
            ],
        )
        inv_line = self._create_invoice_line(
            "in_invoice",
            invoice_line_ids=[{"price_unit": 1000.0, "tax_ids": []}],
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_payable_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": True,
                },
            ],
        )
        line_to_remove = st_line.line_ids[-1]
        line_to_remove_source = line_to_remove.reconciled_lines_ids
        self.assertTrue(line_to_remove.matched_credit_ids)
        self.assertTrue(line_to_remove_source.matched_debit_ids)
        st_line.remove_reconciled_line(st_line.line_ids[-1].id)
        self.assertFalse(line_to_remove_source.matched_debit_ids)

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
            ],
        )

    def test_set_account_negative_statement_line(self):
        st_line = self._create_st_line(-1000.0, update_create_date=False)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
            ],
        )
        account = self.env["account.account"].create(
            {
                "name": "test_validation_using_custom_account",
                "code": "424242",
                "account_type": "asset_current",
            }
        )
        st_line.set_account_bank_statement_line(st_line.line_ids[-1].id, account.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": account.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
            ],
        )

    def test_validation_changed_default_account(self):
        st_line = self._create_st_line(1000.0, update_create_date=False)
        original_journal_account_id = st_line.journal_id.default_account_id
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": original_journal_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.journal_id.default_account_id = self.company_data[
            "default_journal_cash"
        ].default_account_id
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": original_journal_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )

        new_st_line = self._create_st_line(1000.0, update_create_date=False)
        self.assertRecordValues(
            new_st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": new_st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )

    def test_manual_edit_basic_case(self):
        st_line = self._create_st_line(1000.0, update_create_date=False)

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )

        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )

        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id, {"balance": -500, "amount_currency": -500}
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "amount_currency": -500.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -500.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -500.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -500.0,
                    "reconciled": False,
                },
            ],
        )

    def test_manual_edit_change_currency(self):
        self.account_current_assets_1 = self.company_data[
            "default_account_deferred_expense"
        ]
        st_line = self._create_st_line(1000.0, update_create_date=False)

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )

        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_current_assets_1.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_current_assets_1.id,
                    "amount_currency": -1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -1000.0,
                    "reconciled": False,
                },
            ],
        )

        st_line.edit_reconcile_line(
            st_line.line_ids[1].id,
            {
                "balance": -500,
                "amount_currency": -500,
                "currency_id": self.other_currency.id,
            },
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_current_assets_1.id,
                    "amount_currency": -500.0,
                    "currency_id": self.other_currency.id,
                    "balance": -500.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -500.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -500.0,
                    "reconciled": False,
                },
            ],
        )

    def test_res_partner_bank_find_create_multi_account(self):
        partner = self.env["res.partner"].create({"name": "Zitycard"})

        for acc_number in ("123456789", "123456780"):
            st_line = self._create_st_line(
                100.0, account_number=acc_number, update_create_date=False
            )
            inv_line = self._create_invoice_line(
                "out_invoice",
                partner_id=partner.id,
                invoice_line_ids=[{"price_unit": 100.0, "tax_ids": []}],
            )
            st_line.set_line_bank_statement_line(inv_line.id)

        bank_accounts = (
            self.env["res.partner.bank"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("partner_id", "=", partner.id),
                ]
            )
        )
        self.assertEqual(
            len(bank_accounts), 2, "Second bank account was not registered!"
        )

    def test_early_payment_discount_basic_case(self):
        st_line = self._create_st_line(
            90.0, date="2017-01-10", update_create_date=False
        )
        early_pay_acc = self.env.company.account_config_id.account_journal_early_pay_discount_loss_account_id
        inv_line_with_epd = self._create_invoice_line(
            "out_invoice",
            date="2017-01-04",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        st_line.set_line_bank_statement_line(inv_line_with_epd.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 90.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line_with_epd.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": True,
                },
                {
                    "account_id": early_pay_acc.id,
                    "amount_currency": 10.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 10.0,
                    "reconciled": False,
                },
            ],
        )

    def test_early_payment_discount_basic_case_after_date(self):
        inv_line_with_epd = self._create_invoice_line(
            "out_invoice",
            date="2017-01-10",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        st_line = self._create_st_line(
            90.0, date="2017-02-10", update_create_date=False
        )
        st_line.set_line_bank_statement_line(inv_line_with_epd.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 90.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line_with_epd.account_id.id,
                    "amount_currency": -90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -90.0,
                    "reconciled": True,
                },
            ],
        )

    def test_early_payment_discount_basic_case_smaller_amount(self):
        early_pay_acc = self.env.company.account_config_id.account_journal_early_pay_discount_loss_account_id
        st_line = self._create_st_line(
            100.0, date="2017-01-10", update_create_date=False
        )
        inv_line_with_epd = self._create_invoice_line(
            "out_invoice",
            date="2017-01-10",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 90.0}],
        )
        st_line.set_line_bank_statement_line(inv_line_with_epd.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line_with_epd.account_id.id,
                    "amount_currency": -90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -90.0,
                    "reconciled": True,
                },
                {
                    "account_id": early_pay_acc.id,
                    "amount_currency": 9.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 9.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -19.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -19.0,
                    "reconciled": False,
                },
            ],
        )

    def test_exchange_diff_basic_case(self):
        self.other_currency.rate_ids = [
            Command.create(
                {
                    "rate": 1,
                    "name": "2017-01-03",
                }
            )
        ]
        st_line = self._create_st_line(
            100.0,
            date="2017-01-05",
            update_create_date=False,
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            currency_id=self.other_currency.id,
            invoice_date="2017-01-01",
            invoice_line_ids=[{"price_unit": 100.0}],
        )

        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.other_currency.id,
                    "balance": -100.0,
                    "reconciled": True,
                },
            ],
        )

        exchange_move = st_line.line_ids[1].matched_debit_ids.exchange_move_id
        self.assertRecordValues(
            exchange_move,
            [
                {
                    "date": fields.Date.from_string("2017-01-31"),
                    "amount_total_signed": 50,
                }
            ],
        )

    def test_exchange_diff_multiple_lines(self):
        self.other_currency.rate_ids = [
            Command.create(
                {
                    "rate": 1,
                    "name": "2017-01-03",
                }
            )
        ]
        st_line = self._create_st_line(
            200.0,
            date="2017-01-05",
            update_create_date=False,
        )

        inv_line_1 = self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-01",
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        inv_line_2 = self._create_invoice_line(
            "out_invoice",
            currency_id=self.other_currency.id,
            invoice_date="2017-01-01",
            invoice_line_ids=[{"price_unit": 100.0}],
        )

        st_line.set_line_bank_statement_line((inv_line_1 + inv_line_2).ids)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 200.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line_1.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": True,
                },
                {
                    "account_id": inv_line_2.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.other_currency.id,
                    "balance": -100.0,
                    "reconciled": True,
                },
            ],
        )

        self.assertFalse(st_line.line_ids[1].matched_debit_ids.exchange_move_id)
        exchange_move = st_line.line_ids[2].matched_debit_ids.exchange_move_id
        self.assertRecordValues(
            exchange_move,
            [
                {
                    "date": fields.Date.from_string("2017-01-31"),
                    "amount_total_signed": 50,
                }
            ],
        )

    def test_validation_caba_tax_account(self):
        tax_account = self.company_data["default_account_tax_sale"]
        tax_account.reconcile = True

        caba_tax = self.env["account.tax"].create(
            {
                "name": "CABA",
                "amount_type": "percent",
                "amount": 20.0,
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.safe_copy(tax_account).id,
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "account_id": tax_account.id,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "account_id": tax_account.id,
                        }
                    ),
                ],
            }
        )

        st_line = self._create_st_line(120.0, update_create_date=False)
        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 120.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 120.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "amount_currency": -120,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -120,
                    "reconciled": False,
                },
            ],
        )

        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id,
            {
                "tax_ids": [Command.link(caba_tax.id)],
            },
        )

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "amount_currency": 120.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 120.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "tax_ids": caba_tax.ids,
                    "tax_line_id": False,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": False,
                },
                {
                    "account_id": tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": caba_tax.id,
                    "amount_currency": -20.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -20.0,
                    "reconciled": False,
                },
            ],
        )

    def test_multicurrency_flows_all_same_currency(self):
        st_line = self._create_st_line(250.0, update_create_date=False)
        inv_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 100.0}]
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 250.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -150.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -150.0,
                    "reconciled": False,
                },
            ],
        )

        st_line = self._create_st_line(250.0, update_create_date=False)
        inv_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 500.0}]
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 250.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -250.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -250.0,
                    "reconciled": True,
                },
            ],
        )

    def test_multicurrency_flows_currency_transaction_different(self):
        st_line = self._create_st_line(250.0, update_create_date=False)
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 100.0}],
            currency_id=self.other_currency.id,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 250.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.other_currency.id,
                    "balance": -50.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -200.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -200.0,
                    "reconciled": False,
                },
            ],
        )

        st_line = self._create_st_line(250.0, update_create_date=False)
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 500.0}],
            currency_id=self.other_currency.id,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 250.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -500.0,
                    "currency_id": self.other_currency.id,
                    "balance": -250.0,
                    "reconciled": True,
                },
            ],
        )

    def test_multicurrency_flows_currency_journal_different_currency(self):
        new_journal = self.env["account.journal"].create(
            {
                "name": "test",
                "code": "TBNK",
                "type": "bank",
                "currency_id": self.other_currency.id,
            }
        )

        st_line = self._create_st_line(
            250.0, journal_id=new_journal.id, update_create_date=False
        )
        inv_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 100.0}]
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.other_currency.id,
                    "balance": 125.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -50,
                    "currency_id": self.other_currency.id,
                    "balance": -25.0,
                    "reconciled": False,
                },
            ],
        )

        st_line = self._create_st_line(
            250.0, journal_id=new_journal.id, update_create_date=False
        )
        inv_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 500.0}]
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.other_currency.id,
                    "balance": 125.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -125.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -125.0,
                    "reconciled": True,
                },
            ],
        )

    def test_multicurrency_flows_journal_and_transaction_in_other_currency_than_company(
        self,
    ):
        new_journal = self.env["account.journal"].create(
            {
                "name": "test",
                "code": "TBNK",
                "type": "bank",
                "currency_id": self.other_currency.id,
            }
        )
        st_line = self._create_st_line(
            250.0, journal_id=new_journal.id, update_create_date=False
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 100.0}],
            currency_id=self.other_currency.id,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.other_currency.id,
                    "balance": 125.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.other_currency.id,
                    "balance": -50.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -150,
                    "currency_id": self.other_currency.id,
                    "balance": -75.0,
                    "reconciled": False,
                },
            ],
        )

        st_line = self._create_st_line(
            250.0, journal_id=new_journal.id, update_create_date=False
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 500.0}],
            currency_id=self.other_currency.id,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.other_currency.id,
                    "balance": 125.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -250.0,
                    "currency_id": self.other_currency.id,
                    "balance": -125.0,
                    "reconciled": True,
                },
            ],
        )

    def test_multicurrency_flows_triple_currency(self):
        currency_yen = self.setup_other_currency(
            "JPY", rounding=0.001, rates=[("2017-01-01", 10.0)]
        )
        new_journal = self.env["account.journal"].create(
            {
                "name": "test",
                "code": "TBNK",
                "type": "bank",
                "currency_id": self.other_currency.id,
            }
        )
        st_line = self._create_st_line(
            250.0, journal_id=new_journal.id, update_create_date=False
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 100.0}],
            currency_id=currency_yen.id,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.other_currency.id,
                    "balance": 125.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -100.0,
                    "currency_id": currency_yen.id,
                    "balance": -10.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -230,
                    "currency_id": self.other_currency.id,
                    "balance": -115.0,
                    "reconciled": False,
                },
            ],
        )

        st_line = self._create_st_line(
            250.0, journal_id=new_journal.id, update_create_date=False
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 500.0}],
            currency_id=currency_yen.id,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.other_currency.id,
                    "balance": 125.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -500.0,
                    "currency_id": currency_yen.id,
                    "balance": -50.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -150,
                    "currency_id": self.other_currency.id,
                    "balance": -75.0,
                    "reconciled": False,
                },
            ],
        )

        st_line = self._create_st_line(
            250.0, journal_id=new_journal.id, update_create_date=False
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 5000.0}],
            currency_id=currency_yen.id,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 250.0,
                    "currency_id": self.other_currency.id,
                    "balance": 125.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -1250.0,
                    "currency_id": currency_yen.id,
                    "balance": -125.0,
                    "reconciled": True,
                },
            ],
        )

    def test_retrieve_partner_from_account_number(self):
        st_line = self._create_st_line(
            1000.0, partner_id=None, account_number="014 474 8555"
        )
        bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "0144748555",
                "partner_id": self.partner_a.id,
            }
        )
        st_line.partner_id = False
        st_line._set_partner_from_transaction()
        self.assertEqual(st_line.partner_id, bank_account.partner_id)

        self.env["res.partner.bank"].create(
            {
                "acc_number": "0144748555",
                "partner_id": self.partner_b.id,
            }
        )
        st_line.partner_id = False
        st_line._set_partner_from_transaction()
        self.assertEqual(st_line.partner_id, self.env["res.partner"])

        self.partner_a.active = False
        st_line.partner_id = False
        st_line._set_partner_from_transaction()
        self.assertEqual(st_line.partner_id, self.partner_b)

        self.partner_a.active = True
        self.partner_b.active = False
        st_line._set_partner_from_transaction()
        self.assertEqual(st_line.partner_id, self.partner_b)

    def test_retrieve_partner_from_account_number_in_other_company(self):
        st_line = self._create_st_line(
            1000.0,
            partner_id=None,
            account_number="014 474 8555",
            update_create_date=False,
        )
        self.env["res.partner.bank"].create(
            {
                "acc_number": "0144748555",
                "partner_id": self.partner_a.id,
            }
        )

        new_company = self.env["res.company"].create(
            {"name": "test_retrieve_partner_from_account_number_in_other_company"}
        )
        self.partner_a.company_id = new_company
        st_line._set_partner_from_transaction()
        self.assertEqual(st_line.partner_id, self.env["res.partner"])

    def test_retrieve_partner_from_partner_name(self):
        _partner_a, partner_b = self.env["res.partner"].create(
            [
                {"name": "Turlututu tsoin tsoin"},
                {"name": "turlututu"},
            ]
        )

        st_line = self._create_st_line(
            1000.0, partner_id=None, partner_name="Turlututu", update_create_date=False
        )
        self.assertEqual(st_line.partner_id, partner_b)

        self.env["res.partner"].create({"name": "turlututu"})
        st_line.partner_id = False
        st_line._set_partner_from_transaction()
        self.assertFalse(st_line.partner_id)

    def test_retrieve_partner_from_partner_name_odoobot(self):
        odoobot = self.env.ref("base.partner_root")
        odoobot.company_id = self.env.company.id
        st_line = self._create_st_line(
            1000.0,
            partner_id=None,
            partner_name="ODOO",
            update_create_date=False,
        )
        self.assertNotEqual(st_line.partner_id, odoobot)

    def test_retrieve_partner_from_previous_reconciled_st_line(self):
        _partner_a, partner_b = self.env["res.partner"].create(
            [
                {"name": "Turlututu"},
                {"name": "Turlututu"},
            ]
        )

        st_line = self._create_st_line(
            1000.0, partner_id=None, partner_name="Turlututu", update_create_date=False
        )
        st_line_2 = self._create_st_line(
            1000.0,
            partner_id=partner_b.id,
            partner_name="Turlututu",
            update_create_date=False,
        )
        inv_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 1000.0}]
        )
        st_line_2.set_line_bank_statement_line(inv_line.id)

        st_line._set_partner_from_transaction()
        self.assertEqual(st_line.partner_id, partner_b)

    def test_retrieve_partner_with_multiple_st_line(self):
        _partner_a, partner_b, partner_c = self.env["res.partner"].create(
            [
                {"name": "Turlututu"},
                {"name": "Turlututu"},
                {"name": "Turlututu tsoin tsoin"},
            ]
        )
        bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "0144748555",
                "partner_id": self.partner_a.id,
            }
        )

        st_line_1 = self._create_st_line(
            1000.0,
            partner_id=partner_b.id,
            partner_name="Turlututu",
            update_create_date=False,
        )
        inv_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 1000.0}]
        )
        st_line_1.set_line_bank_statement_line(inv_line.id)

        st_line_2 = self._create_st_line(
            1000.0, partner_id=None, partner_name="Turlututu", update_create_date=False
        )
        st_line_3 = self._create_st_line(
            1000.0, partner_id=None, account_number="014 474 8555"
        )
        st_line_4 = self._create_st_line(
            1000.0, partner_id=None, partner_name="Turlututu tsoin tsoin"
        )
        st_lines = st_line_2 + st_line_3 + st_line_4
        st_lines.write({"partner_id": False})
        st_lines._set_partner_from_transaction()
        self.assertEqual(st_line_2.partner_id, partner_b)
        self.assertEqual(st_line_3.partner_id, bank_account.partner_id)
        self.assertEqual(st_line_4.partner_id, partner_c)

    def test_retrieve_partner_with_multiple_matches(self):
        partner_a, _partner_b = self.env["res.partner"].create(
            [
                {"name": "Bobybob"},
                {"name": "Turlututu"},
            ]
        )
        bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "123456789",
                "partner_id": partner_a.id,
            }
        )
        st_line = self._create_st_line(
            1000.0,
            partner_id=None,
            account_number="123456789",
            partner_name="Turlututu",
            update_create_date=False,
        )
        st_line._set_partner_from_transaction()
        self.assertEqual(st_line.partner_id, bank_account.partner_id)

    def test_res_partner_bank_find_create_when_archived(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Zitycard",
                "bank_ids": [
                    Command.create(
                        {
                            "acc_number": "123456789",
                            "active": False,
                        }
                    )
                ],
            }
        )

        st_line = self._create_st_line(
            100.0,
            partner_name="Zeumat Zitycard",
            account_number="123456789",
            update_create_date=False,
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            partner_id=partner.id,
            invoice_line_ids=[{"price_unit": 100.0, "tax_ids": []}],
        )
        st_line.set_line_bank_statement_line(inv_line.id)

        self.env["res.partner.bank"].flush_model()

    def test_res_partner_bank_find_create_multi_company(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Zitycard",
                "bank_ids": [Command.create({"acc_number": "123456789"})],
            }
        )
        partner.bank_ids.company_id = self.company_data_2["company"]
        self.env.user.company_ids = self.env.company

        st_line = self._create_st_line(
            100.0,
            partner_name="Zeumat Zitycard",
            account_number="123456789",
            update_create_date=False,
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            partner_id=partner.id,
            invoice_line_ids=[{"price_unit": 100.0, "tax_ids": []}],
        )
        st_line.set_line_bank_statement_line(inv_line.id)

        self.env["res.partner.bank"].flush_model()

    def test_validation_exchange_difference_draft_invoice(self):
        inv_line = self._create_invoice_line(
            "out_invoice",
            currency_id=self.other_currency.id,
            invoice_date="2016-01-01",
            invoice_line_ids=[{"price_unit": 240.0}],
        )
        inv_line.move_id.action_draft()
        self.assertEqual(inv_line.move_id.state, "draft")
        self.assertAlmostEqual(inv_line.amount_residual, 80.0)

        st_line_1 = self._create_st_line(
            60.0,
            date="2017-01-01",
            foreign_currency_id=self.other_currency.id,
            amount_currency=120.0,
            update_create_date=False,
        )
        st_line_1.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line_1.line_ids.sorted(),
            [
                {
                    "account_id": st_line_1.journal_id.default_account_id.id,
                    "amount_currency": 60.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 60.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "amount_currency": -120.0,
                    "currency_id": self.other_currency.id,
                    "balance": -60.0,
                    "reconciled": True,
                },
            ],
        )

        partials = st_line_1.line_ids.matched_debit_ids
        exchange_move = partials.exchange_move_id
        _liquidity_line, _suspense_line, other_line = st_line_1._seek_for_lines()
        self.assertRecordValues(
            partials.sorted(),
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": inv_line.id,
                    "credit_move_id": other_line.id,
                    "exchange_move_id": exchange_move.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": exchange_move.line_ids.sorted()[0].id,
                    "credit_move_id": other_line.id,
                    "exchange_move_id": False,
                },
            ],
        )

        self.assertEqual(exchange_move.state, "draft")
        self.assertRecordValues(
            exchange_move.line_ids.sorted(),
            [
                {
                    "account_id": inv_line.account_id.id,
                    "amount_currency": 0.0,
                    "currency_id": self.other_currency.id,
                    "balance": 20.0,
                    "reconciled": True,
                },
                {
                    "account_id": self.env.company.account_config_id.income_currency_exchange_account_id.id,
                    "amount_currency": 0.0,
                    "currency_id": self.other_currency.id,
                    "balance": -20.0,
                    "reconciled": False,
                },
            ],
        )
        self.assertEqual(inv_line.move_id.payment_state, "partial")
        self.assertAlmostEqual(inv_line.amount_residual, 40.0)

        inv_line.move_id.line_ids.filtered(
            lambda x: x.display_type == "product"
        ).price_unit = 290
        inv_line.move_id.action_post()
        self.assertEqual(inv_line.move_id.payment_state, "not_paid")
        partials = st_line_1.line_ids.matched_debit_ids
        exchange_move = partials.exchange_move_id
        self.assertEqual(exchange_move, self.env["account.move"])

        inv_line.move_id.action_draft()
        inv_line.move_id.line_ids.filtered(
            lambda x: x.display_type == "product"
        ).price_unit = 240
        self.assertAlmostEqual(inv_line.amount_residual, 80.0)

        st_line_2 = self._create_st_line(
            60.0,
            date="2017-01-01",
            foreign_currency_id=self.other_currency.id,
            amount_currency=120.0,
            update_create_date=False,
        )
        st_line_2.set_line_bank_statement_line(inv_line.id)

        partials = st_line_2.line_ids.matched_debit_ids
        exchange_move = partials.exchange_move_id
        self.assertEqual(exchange_move.state, "draft")
        self.assertEqual(inv_line.move_id.payment_state, "partial")
        self.assertAlmostEqual(inv_line.amount_residual, 40.0)

        inv_line.ref = "new reference"
        inv_line.move_id.action_post()
        self.assertEqual(inv_line.move_id.payment_state, "partial")
        self.assertAlmostEqual(inv_line.amount_residual, 40.0)
        self.assertEqual(exchange_move.state, "posted")

    def test_validation_expense_exchange_difference(self):
        expense_exchange_account = (
            self.env.company.account_config_id.expense_currency_exchange_account_id
        )

        st_line = self._create_st_line(
            1200.0,
            date="2016-01-01",
            update_create_date=False,
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            currency_id=self.other_currency.id,
            invoice_date="2017-01-01",
            invoice_line_ids=[{"price_unit": 3600.0}],
        )

        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1200.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1200.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "amount_currency": -3600.0,
                    "currency_id": self.other_currency.id,
                    "balance": -1200.0,
                    "reconciled": True,
                },
            ],
        )
        self.assertRecordValues(st_line, [{"is_reconciled": True}])
        self.assertRecordValues(inv_line.move_id, [{"payment_state": "paid"}])
        self.assertRecordValues(
            inv_line.matched_credit_ids.exchange_move_id.line_ids,
            [
                {
                    "account_id": inv_line.account_id.id,
                    "amount_currency": 0.0,
                    "currency_id": self.other_currency.id,
                    "balance": -600.0,
                    "reconciled": True,
                    "date": fields.Date.from_string("2017-01-31"),
                },
                {
                    "account_id": expense_exchange_account.id,
                    "amount_currency": 0.0,
                    "currency_id": self.other_currency.id,
                    "balance": 600.0,
                    "reconciled": False,
                    "date": fields.Date.from_string("2017-01-31"),
                },
            ],
        )

    def test_validation_income_exchange_difference(self):
        income_exchange_account = (
            self.env.company.account_config_id.income_currency_exchange_account_id
        )

        st_line = self._create_st_line(
            1800.0,
            date="2017-01-01",
            update_create_date=False,
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            currency_id=self.other_currency.id,
            invoice_date="2016-01-01",
            invoice_line_ids=[{"price_unit": 3600.0}],
        )

        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1800.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1800.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "amount_currency": -3600.0,
                    "currency_id": self.other_currency.id,
                    "balance": -1800.0,
                    "reconciled": True,
                },
            ],
        )
        self.assertRecordValues(st_line, [{"is_reconciled": True}])
        self.assertRecordValues(inv_line.move_id, [{"payment_state": "paid"}])
        self.assertRecordValues(
            inv_line.matched_credit_ids.exchange_move_id.line_ids,
            [
                {
                    "account_id": inv_line.account_id.id,
                    "amount_currency": 0.0,
                    "currency_id": self.other_currency.id,
                    "balance": 600.0,
                    "reconciled": True,
                    "date": fields.Date.from_string("2017-01-31"),
                },
                {
                    "account_id": income_exchange_account.id,
                    "amount_currency": 0.0,
                    "currency_id": self.other_currency.id,
                    "balance": -600.0,
                    "reconciled": False,
                    "date": fields.Date.from_string("2017-01-31"),
                },
            ],
        )

    def test_validation_exchange_diff_multiple(self):
        income_exchange_account = (
            self.env.company.account_config_id.income_currency_exchange_account_id
        )
        foreign_currency = self.setup_other_currency(
            "AED", rates=[("2016-01-01", 6.0), ("2017-01-01", 5.0)]
        )

        st_line = self._create_st_line(
            1200.0,
            date="2016-01-01",
            foreign_currency_id=foreign_currency.id,
            amount_currency=6000.0,
            update_create_date=False,
        )
        inv_line_1 = self._create_invoice_line(
            "out_invoice",
            currency_id=foreign_currency.id,
            invoice_date="2016-01-01",
            invoice_line_ids=[{"price_unit": 1000.0}],
        )
        inv_line_2 = self._create_invoice_line(
            "out_invoice",
            currency_id=foreign_currency.id,
            invoice_date="2017-01-01",
            invoice_line_ids=[{"price_unit": 2000.0}],
        )
        inv_line_3 = self._create_invoice_line(
            "out_invoice",
            currency_id=foreign_currency.id,
            invoice_date="2016-01-01",
            invoice_line_ids=[{"price_unit": 3000.0}],
        )

        st_line.set_line_bank_statement_line((inv_line_1 + inv_line_2 + inv_line_3).ids)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1200.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1200.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line_1.account_id.id,
                    "amount_currency": -1000.0,
                    "currency_id": foreign_currency.id,
                    "balance": -200.0,
                    "reconciled": True,
                },
                {
                    "account_id": inv_line_2.account_id.id,
                    "amount_currency": -2000.0,
                    "currency_id": foreign_currency.id,
                    "balance": -400.0,
                    "reconciled": True,
                },
                {
                    "account_id": inv_line_3.account_id.id,
                    "amount_currency": -3000.0,
                    "currency_id": foreign_currency.id,
                    "balance": -600.0,
                    "reconciled": True,
                },
            ],
        )
        self.assertRecordValues(st_line, [{"is_reconciled": True}])
        self.assertRecordValues(inv_line_1.move_id, [{"payment_state": "paid"}])
        self.assertRecordValues(inv_line_2.move_id, [{"payment_state": "paid"}])
        self.assertRecordValues(inv_line_3.move_id, [{"payment_state": "paid"}])
        self.assertRecordValues(
            (
                inv_line_1 + inv_line_2 + inv_line_3
            ).matched_credit_ids.exchange_move_id.line_ids,
            [
                {
                    "account_id": inv_line_1.account_id.id,
                    "amount_currency": 0.0,
                    "currency_id": foreign_currency.id,
                    "balance": 33.33,
                    "reconciled": True,
                },
                {
                    "account_id": income_exchange_account.id,
                    "amount_currency": 0.0,
                    "currency_id": foreign_currency.id,
                    "balance": -33.33,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line_3.account_id.id,
                    "amount_currency": 0.0,
                    "currency_id": foreign_currency.id,
                    "balance": 100.0,
                    "reconciled": True,
                },
                {
                    "account_id": income_exchange_account.id,
                    "amount_currency": 0.0,
                    "currency_id": foreign_currency.id,
                    "balance": -100.0,
                    "reconciled": False,
                },
            ],
        )

    def test_early_payment_included_intracomm_bill(self):
        tax_tags = self.env["account.account.tag"].create(
            [
                {
                    "name": f"tax_tag_{i}",
                    "applicability": "taxes",
                    "country_id": self.env.company.account_config_id.account_fiscal_country_id.id,
                }
                for i in range(6)
            ]
        )

        intracomm_tax = self.env["account.tax"].create(
            {
                "name": "tax20",
                "amount_type": "percent",
                "amount": 20,
                "type_tax_use": "purchase",
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                            "factor_percent": 100.0,
                            "tag_ids": [Command.set(tax_tags[0].ids)],
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "factor_percent": 100.0,
                            "tag_ids": [Command.set(tax_tags[1].ids)],
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "factor_percent": -100.0,
                            "tag_ids": [Command.set(tax_tags[2].ids)],
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                            "factor_percent": 100.0,
                            "tag_ids": [Command.set(tax_tags[3].ids)],
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "factor_percent": 100.0,
                            "tag_ids": [Command.set(tax_tags[4].ids)],
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "factor_percent": -100.0,
                            "tag_ids": [Command.set(tax_tags[5].ids)],
                        }
                    ),
                ],
            }
        )

        early_payment_term = self.env["account.payment.term"].create(
            {
                "name": "early_payment_term",
                "company_id": self.company_data["company"].id,
                "early_pay_discount_computation": "included",
                "early_discount": True,
                "discount_percentage": 2,
                "discount_days": 7,
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100.0,
                            "nb_days": 30,
                        }
                    ),
                ],
            }
        )

        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_payment_term_id": early_payment_term.id,
                "invoice_date": "2019-01-01",
                "date": "2019-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "price_unit": 1000.0,
                            "tax_ids": [Command.set(intracomm_tax.ids)],
                        }
                    ),
                ],
            }
        )
        bill.action_post()

        st_line = self._create_st_line(
            -980.0,
            date="2017-01-01",
            update_create_date=False,
        )

        st_line.set_line_bank_statement_line(
            bill.line_ids.filtered(lambda x: x.account_type == "liability_payable").ids
        )

        self.assertRecordValues(
            st_line.line_ids.sorted("balance"),
            [
                {"amount_currency": -980.0, "tax_ids": [], "tax_tag_ids": []},
                {
                    "amount_currency": -20.0,
                    "tax_ids": intracomm_tax.ids,
                    "tax_tag_ids": tax_tags[3].ids,
                },
                {
                    "amount_currency": -4.0,
                    "tax_ids": [],
                    "tax_tag_ids": tax_tags[4].ids,
                },
                {"amount_currency": 4.0, "tax_ids": [], "tax_tag_ids": tax_tags[5].ids},
                {"amount_currency": 1000.0, "tax_ids": [], "tax_tag_ids": []},
            ],
        )

    def test_partial_reconciliation_suggestion_with_mixed_invoice_and_refund(self):
        st_line = self._create_st_line(
            1800.0,
            date="2017-01-01",
            foreign_currency_id=self.other_currency.id,
            amount_currency=3600.0,
            update_create_date=False,
        )

        inv1 = self._create_invoice_line(
            "out_invoice",
            currency_id=self.other_currency.id,
            invoice_date="2016-01-01",
            invoice_line_ids=[{"price_unit": 2400.0}],
        )
        inv2 = self._create_invoice_line(
            "out_invoice",
            currency_id=self.other_currency.id,
            invoice_date="2016-01-01",
            invoice_line_ids=[{"price_unit": 600.0}],
        )
        refund = self._create_invoice_line(
            "out_refund",
            currency_id=self.other_currency.id,
            invoice_date="2016-01-01",
            invoice_line_ids=[{"price_unit": 1200.0}],
        )
        st_line.set_line_bank_statement_line(inv1.id)

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1800.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1800.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "amount_currency": -2400.0,
                    "currency_id": self.other_currency.id,
                    "balance": -1200.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1200.0,
                    "currency_id": self.other_currency.id,
                    "balance": -600.0,
                    "reconciled": False,
                },
            ],
        )
        exchange_move_1 = st_line.line_ids[1].matched_debit_ids.exchange_move_id
        self.assertRecordValues(
            exchange_move_1,
            [
                {
                    "date": fields.Date.from_string("2017-01-31"),
                    "amount_total_signed": 400,
                }
            ],
        )

        st_line.set_line_bank_statement_line(inv2.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1800.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1800.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "amount_currency": -2400.0,
                    "currency_id": self.other_currency.id,
                    "balance": -1200.0,
                    "reconciled": True,
                },
                {
                    "account_id": inv2.account_id.id,
                    "amount_currency": -600.0,
                    "currency_id": self.other_currency.id,
                    "balance": -300.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -600.0,
                    "currency_id": self.other_currency.id,
                    "balance": -300.0,
                    "reconciled": False,
                },
            ],
        )
        exchange_move_2 = st_line.line_ids[2].matched_debit_ids.exchange_move_id
        self.assertRecordValues(
            exchange_move_2,
            [
                {
                    "date": fields.Date.from_string("2017-01-31"),
                    "amount_total_signed": 100,
                }
            ],
        )

        st_line.set_line_bank_statement_line(refund.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1800.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 1800.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "amount_currency": -2400.0,
                    "currency_id": self.other_currency.id,
                    "balance": -1200.0,
                    "reconciled": True,
                },
                {
                    "account_id": inv2.account_id.id,
                    "amount_currency": -600.0,
                    "currency_id": self.other_currency.id,
                    "balance": -300.0,
                    "reconciled": True,
                },
                {
                    "account_id": refund.account_id.id,
                    "amount_currency": 1200.0,
                    "currency_id": self.other_currency.id,
                    "balance": 600.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -1800.0,
                    "currency_id": self.other_currency.id,
                    "balance": -900.0,
                    "reconciled": False,
                },
            ],
        )
        exchange_move_3 = st_line.line_ids[3].matched_credit_ids.exchange_move_id
        self.assertRecordValues(
            exchange_move_3,
            [
                {
                    "date": fields.Date.from_string("2017-01-31"),
                    "amount_total_signed": 200.0,
                }
            ],
        )

    def test_reconciliation_with_branch(self):
        company = self.company_data["company"]
        branch = self.env["res.company"].create(
            {
                "name": "Branch A",
                "parent_id": company.id,
            }
        )
        self.cr.precommit.run()

        partner_branch = self.env["res.partner"].create(
            {
                "name": "Partner Branch",
                "company_id": branch.id,
            }
        )

        aml_branch = self._create_invoice_line(
            "out_invoice",
            company_id=branch.id,
            partner_id=partner_branch.id,
            invoice_date="2019-01-01",
            invoice_line_ids=[{"name": "Test reco", "quantity": 1, "price_unit": 1000}],
        )
        st_line_main = self._create_st_line(
            1000.0,
            company_id=company.id,
            date="2019-01-01",
            payment_ref="Test reco",
        )
        st_line_branch = self._create_st_line(
            1000.0,
            company_id=branch.id,
            date="2019-01-01",
            payment_ref="Test reco2",
            partner_id=partner_branch.id,
        )

        st_line_main.set_line_bank_statement_line(aml_branch.ids)
        self.assertFalse(st_line_main.partner_id)

        st_line_main.action_undo_reconciliation()

        st_line_branch.set_line_bank_statement_line(aml_branch.ids)
        self.assertEqual(
            st_line_branch.partner_id,
            partner_branch,
            "The partner should remain set on the transaction for the branch company.",
        )

        st_line_branch.action_undo_reconciliation()

        st_line_branch.partner_id = False
        st_line_branch.set_line_bank_statement_line(aml_branch.ids)
        self.assertEqual(
            st_line_branch.partner_id,
            partner_branch,
            "The partner should be automatically set on the transaction for the branch company if it's set on the aml.",
        )

    def test_residual_amount_same_currency(self):
        st_line_1 = self._create_st_line(
            20.0,
            date="2017-01-01",
            update_create_date=False,
        )
        st_line_2 = self._create_st_line(
            100.0,
            date="2017-01-01",
            update_create_date=False,
        )
        inv1 = self._create_invoice_line(
            "out_invoice",
            invoice_date="2016-01-01",
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        st_line_1.set_line_bank_statement_line(inv1.id)
        self.assertRecordValues(
            st_line_1.line_ids,
            [
                {
                    "account_id": st_line_1.journal_id.default_account_id.id,
                    "amount_currency": 20.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 20.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "amount_currency": -20.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -20.0,
                    "reconciled": True,
                },
            ],
        )
        self.assertEqual(inv1.amount_residual, 80)
        self.assertEqual(inv1.move_id.payment_state, "partial")

        st_line_2.set_line_bank_statement_line(inv1.id)
        self.assertRecordValues(
            st_line_2.line_ids,
            [
                {
                    "account_id": st_line_2.journal_id.default_account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "amount_currency": -80.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -80.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line_2.journal_id.suspense_account_id.id,
                    "amount_currency": -20.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -20.0,
                    "reconciled": False,
                },
            ],
        )
        self.assertEqual(inv1.amount_residual, 0)
        self.assertEqual(inv1.move_id.payment_state, "paid")

    def test_residual_amount_other_currency(self):
        st_line_1 = self._create_st_line(
            20.0,
            date="2017-01-01",
            update_create_date=False,
        )
        st_line_2 = self._create_st_line(
            100.0,
            date="2017-01-01",
            update_create_date=False,
        )
        inv1 = self._create_invoice_line(
            "out_invoice",
            currency_id=self.other_currency.id,
            invoice_date="2017-01-01",
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        st_line_1.set_line_bank_statement_line(inv1.id)
        self.assertRecordValues(
            st_line_1.line_ids,
            [
                {
                    "account_id": st_line_1.journal_id.default_account_id.id,
                    "amount_currency": 20.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 20.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "amount_currency": -40.0,
                    "currency_id": self.other_currency.id,
                    "balance": -20.0,
                    "reconciled": True,
                },
            ],
        )
        self.assertEqual(inv1.amount_residual_currency, 60)
        self.assertEqual(inv1.move_id.payment_state, "partial")

        st_line_2.set_line_bank_statement_line(inv1.id)
        self.assertRecordValues(
            st_line_2.line_ids,
            [
                {
                    "account_id": st_line_2.journal_id.default_account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "amount_currency": -60.0,
                    "currency_id": self.other_currency.id,
                    "balance": -30.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line_2.journal_id.suspense_account_id.id,
                    "amount_currency": -70.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -70.0,
                    "reconciled": False,
                },
            ],
        )
        self.assertEqual(inv1.amount_residual_currency, 0)
        self.assertEqual(inv1.move_id.payment_state, "paid")

    def test_adding_multiple_invoice_at_once(self):
        statement_line = self._create_st_line(amount=160, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 25.0}]
        )
        move_line_2 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 50.0}]
        )
        move_line_3 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 100.0}]
        )

        statement_line.set_line_bank_statement_line(
            (move_line_1 + move_line_2 + move_line_3).ids
        )
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": 160.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 160.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": -25.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -25.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": -50.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -50.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": -85.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -85.0,
                    "reconciled": True,
                },
            ],
        )

    def test_adding_multiple_bill_at_once(self):
        statement_line = self._create_st_line(amount=-160, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "in_invoice", invoice_line_ids=[{"price_unit": 25.0}]
        )
        move_line_2 = self._create_invoice_line(
            "in_invoice", invoice_line_ids=[{"price_unit": 50.0}]
        )
        move_line_3 = self._create_invoice_line(
            "in_invoice", invoice_line_ids=[{"price_unit": 100.0}]
        )

        statement_line.set_line_bank_statement_line(
            (move_line_1 + move_line_2 + move_line_3).ids
        )
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": -160.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -160.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 25.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 25.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": 50.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 50.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": 85.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 85.0,
                    "reconciled": True,
                },
            ],
        )

    def test_adding_multiple_moves_and_then_more(self):
        statement_line = self._create_st_line(amount=160, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 25.0}]
        )
        move_line_2 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 50.0}]
        )
        move_line_3 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 100.0}]
        )
        move_line_4 = self._create_invoice_line(
            "in_invoice", invoice_line_ids=[{"price_unit": 25.0}]
        )

        statement_line.set_line_bank_statement_line(
            (move_line_1 + move_line_2 + move_line_3 + move_line_4).ids
        )
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": 160.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 160.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": -25.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -25.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": -50.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -50.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_4.account_id.id,
                    "amount_currency": 25.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 25.0,
                    "reconciled": True,
                },
                {
                    "account_id": statement_line.journal_id.suspense_account_id.id,
                    "amount_currency": -10.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )

        move_line_5 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 20.0}]
        )
        statement_line.set_line_bank_statement_line(move_line_5.id)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": 160.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 160.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": -25.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -25.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": -50.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -50.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_4.account_id.id,
                    "amount_currency": 25.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 25.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_5.account_id.id,
                    "amount_currency": -10.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -10.0,
                    "reconciled": True,
                },
            ],
        )

    def test_adding_multiple_moves_and_then_more_multi_currencies(self):
        statement_line = self._create_st_line(amount=160, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 25.0}]
        )
        move_line_2 = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 100.0}],
            currency_id=self.other_currency.id,
        )
        move_line_3 = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 100.0}]
        )
        move_line_4 = self._create_invoice_line(
            "in_invoice",
            invoice_line_ids=[{"price_unit": 50.0}],
            currency_id=self.other_currency.id,
        )
        statement_line.set_line_bank_statement_line(
            (move_line_1 + move_line_2 + move_line_3 + move_line_4).ids
        )
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": 160.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 160.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": -25.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -25.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.other_currency.id,
                    "balance": -50.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_4.account_id.id,
                    "amount_currency": 50.0,
                    "currency_id": self.other_currency.id,
                    "balance": 25.0,
                    "reconciled": True,
                },
                {
                    "account_id": statement_line.journal_id.suspense_account_id.id,
                    "amount_currency": -10.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )

    def test_partial_auto_tolerance(self):
        self.env["ir.config_parameter"].set_param(
            "account.bank_rec_payment_tolerance", "0.03"
        )
        inv1 = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_date="2020-01-01",
            invoice_line_ids=[{"price_unit": 500.0}],
        )
        st_line = self._create_st_line(
            450.0,
            date="2020-01-05",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        st_line._try_auto_reconcile_statement_lines()
        self.assertFalse(st_line.is_reconciled)
        st_line = self._create_st_line(
            490.0,
            date="2020-01-05",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        st_line._try_auto_reconcile_statement_lines()

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "balance": 490.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "balance": -500.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "balance": 10.0,
                    "reconciled": False,
                },
            ],
        )

        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        reco_model = self.env["account.reconcile.model"].search(
            [
                ("is_bank_fee_model", "=", True),
                ("match_journal_ids", "in", st_line.journal_id.ids),
            ],
            limit=1,
        )
        self.assertTrue(
            reco_model, "A new reco model for fees should have been created"
        )

        self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_date="2020-01-01",
            invoice_line_ids=[{"price_unit": 500.0}],
        )
        st_line = self._create_st_line(
            490.0,
            date="2020-01-05",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        st_line._try_auto_reconcile_statement_lines()
        self.assertEqual(
            st_line.line_ids[-1].reconcile_model_id,
            reco_model,
            "The fees reco model should be assigned to a new line that is close to the invoice",
        )

    def test_partial_auto_tolerance_different_amount(self):
        self.env["ir.config_parameter"].set_param(
            "account.bank_rec_payment_tolerance", "0.05"
        )
        inv = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_date="2020-01-01",
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        st_line = self._create_st_line(
            90.0,
            date="2020-01-05",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        st_line.set_line_bank_statement_line(inv.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "balance": 90.0,
                    "reconciled": False,
                },
                {"account_id": inv.account_id.id, "balance": -90.0, "reconciled": True},
            ],
        )
        inv = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_date="2020-01-01",
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        st_line = self._create_st_line(
            96.0,
            date="2020-01-05",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        st_line.set_line_bank_statement_line(inv.id)

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "balance": 96.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv.account_id.id,
                    "balance": -100.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "balance": 4.0,
                    "reconciled": False,
                },
            ],
        )

        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        reco_model = self.env["account.reconcile.model"].search(
            [
                ("is_bank_fee_model", "=", True),
                ("match_journal_ids", "in", st_line.journal_id.ids),
            ],
            limit=1,
        )
        self.assertTrue(
            reco_model, "A new reco model for fees should have been created"
        )

        inv = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_date="2020-01-01",
            invoice_line_ids=[{"price_unit": 500.0}],
        )
        st_line = self._create_st_line(
            490.0,
            date="2020-01-05",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        st_line._try_auto_reconcile_statement_lines()
        self.assertEqual(
            st_line.line_ids[-1].reconcile_model_id,
            reco_model,
            "The fees reco model should be assigned to a new line that is close to the invoice",
        )

    def test_partial_auto_tolerance_multicurrency(self):
        self.env["ir.config_parameter"].set_param(
            "account.bank_rec_payment_tolerance", "0.03"
        )
        other_currency = self.setup_other_currency(
            "JPY", rates=[("2020-01-01", 10.0), ("2020-01-20", 9.9)]
        )
        inv1 = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            currency_id=other_currency.id,
            invoice_date="2020-01-20",
            invoice_line_ids=[{"price_unit": 4950.0}],
        )
        st_line = self._create_st_line(
            485.0,
            date="2020-01-01",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        st_line.set_line_bank_statement_line([inv1.id])

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 485.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 485.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "amount_currency": -4950.0,
                    "currency_id": other_currency.id,
                    "balance": -495.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": 10.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 10.0,
                    "reconciled": False,
                },
            ],
        )
        self.assertEqual(inv1.amount_residual, 0)

        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        reco_model = self.env["account.reconcile.model"].search(
            [
                ("is_bank_fee_model", "=", True),
                ("match_journal_ids", "in", st_line.journal_id.ids),
            ],
            limit=1,
        )
        self.assertTrue(
            reco_model, "A new reco model for fees should have been created"
        )
        inv1 = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            currency_id=other_currency.id,
            invoice_date="2020-01-20",
            invoice_line_ids=[{"price_unit": 4950.0}],
        )
        st_line = self._create_st_line(
            485.0,
            date="2020-01-01",
            partner_id=self.partner_a.id,
            payment_ref=inv1.name,
            update_create_date=False,
        )
        st_line._try_auto_reconcile_statement_lines()
        self.assertEqual(
            st_line.line_ids[-1].reconcile_model_id,
            reco_model,
            "The fees reco model should be assigned to a new line that is close to the invoice",
        )

    def test_partial_auto_tolerance_st_line_foreign_currency(self):
        self.env["ir.config_parameter"].set_param(
            "account.bank_rec_payment_tolerance", "0.03"
        )
        other_currency = self.setup_other_currency("JPY", rates=[("2020-01-01", 9.5)])
        inv1 = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_date="2020-01-20",
            invoice_line_ids=[{"price_unit": 495.0}],
        )
        st_line = self._create_st_line(
            485.0,
            date="2020-01-01",
            foreign_currency_id=other_currency.id,
            partner_id=self.partner_a.id,
            update_create_date=False,
            amount_currency=4900,
        )
        st_line.set_line_bank_statement_line([inv1.id])

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 485.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 485.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv1.account_id.id,
                    "amount_currency": -495.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -495.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": 95.0,
                    "currency_id": other_currency.id,
                    "balance": 10.0,
                    "reconciled": False,
                },
            ],
        )
        self.assertEqual(inv1.amount_residual, 0)

        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        reco_model = self.env["account.reconcile.model"].search(
            [
                ("is_bank_fee_model", "=", True),
                ("match_journal_ids", "in", st_line.journal_id.ids),
            ],
            limit=1,
        )
        self.assertTrue(
            reco_model, "A new reco model for fees should have been created"
        )

    def test_do_not_tolerate_if_rec_from_invoice(self):
        self.env["ir.config_parameter"].set_param(
            "account.bank_rec_payment_tolerance", "0.03"
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_date="2020-01-01",
            invoice_line_ids=[{"price_unit": 500.0}],
        )
        move = inv_line.move_id
        st_line = self._create_st_line(
            490.0,
            date="2020-01-05",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        move.js_add_outstanding_line(st_line.line_ids[0].id)
        self.assertEqual(move.display_state, "partial")
        self.assertEqual(10, inv_line.amount_residual)
        inv_line = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_date="2020-01-01",
            invoice_line_ids=[{"price_unit": 500.0}],
        )
        move = inv_line.move_id
        st_line = self._create_st_line(
            490.0,
            date="2020-01-05",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertEqual(move.display_state, "paid")

    def test_auto_match_multiple_candidates_tolerance(self):
        move_line = self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-10",
            invoice_line_ids=[{"price_unit": 149.5}],
        )
        statement_line = self._create_st_line(
            amount=150,
            partner_id=self.partner_a.id,
            date="2017-01-08",
            update_create_date=False,
        )
        statement_line._try_auto_reconcile_statement_lines()
        self.assertFalse(statement_line.line_ids.reconciled_lines_ids)

        self.env["ir.config_parameter"].set_param(
            "account.bank_rec_payment_tolerance", "0.03"
        )
        statement_line = self._create_st_line(
            amount=150,
            partner_id=self.partner_a.id,
            date="2017-01-08",
            update_create_date=False,
        )
        statement_line._try_auto_reconcile_statement_lines()
        self.assertEqual(statement_line.line_ids.reconciled_lines_ids, move_line)

    def test_exchange_diff_single_currency(self):
        currency_yen = self.setup_other_currency(
            "JPY", rounding=1.0, rates=[("2017-01-01", 133.62)]
        )
        new_journal = self.env["account.journal"].create(
            {
                "name": "test",
                "code": "TBNK",
                "type": "bank",
                "currency_id": currency_yen.id,
            }
        )
        st_line = self._create_st_line(
            50.0, journal_id=new_journal.id, update_create_date=False
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 100.0}],
            currency_id=currency_yen.id,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 50.0,
                    "currency_id": currency_yen.id,
                    "balance": 0.37,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -50.0,
                    "currency_id": currency_yen.id,
                    "balance": -0.37,
                    "reconciled": True,
                },
            ],
        )
        self.assertFalse(st_line.line_ids[1].matched_debit_ids.exchange_move_id)

    def test_multi_currency_with_foreign(self):
        currency_yen = self.setup_other_currency(
            "JPY", rounding=1.0, rates=[("2017-01-01", 10.00)]
        )
        new_journal = self.env["account.journal"].create(
            {
                "name": "test",
                "code": "TBNK",
                "type": "bank",
                "currency_id": currency_yen.id,
            }
        )
        st_line = self._create_st_line(
            1000.0,
            journal_id=new_journal.id,
            update_create_date=False,
            foreign_currency_id=self.company_data["currency"].id,
        )
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 100.0}],
            currency_id=self.other_currency.id,
        )
        st_line.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": currency_yen.id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.other_currency.id,
                    "balance": -50.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -50.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -50.0,
                    "reconciled": False,
                },
            ],
        )
        inv_line2 = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 50.0}],
            currency_id=self.company_data["currency"].id,
        )
        st_line.set_line_bank_statement_line(inv_line2.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": currency_yen.id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.other_currency.id,
                    "balance": -50.0,
                    "reconciled": True,
                },
                {
                    "account_id": inv_line2.account_id.id,
                    "amount_currency": -50.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -50.0,
                    "reconciled": True,
                },
            ],
        )

    def test_delete_line_with_reco_model(self):
        reco_model = self.env["account.reconcile.model"].create(
            {
                "name": "test reco model",
                "match_journal_ids": [
                    Command.set([self.company_data["default_journal_bank"].id])
                ],
                "match_label": "contains",
                "match_label_param": "blblbl",
                "line_ids": [
                    Command.create(
                        {"account_id": self.company_data["default_account_revenue"].id}
                    )
                ],
            }
        )
        st_line = self._create_st_line(
            500.0,
            date="2020-01-01",
            payment_ref="blblbl",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        reco_model._apply_reconcile_models(st_line)
        self.assertEqual(
            st_line.line_ids[-1].reconcile_model_id,
            reco_model,
            "The test reco model should be assigned",
        )
        reco_model._trigger_reconciliation_model(st_line)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 500.0,
                    "balance": 500.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.company_data["default_account_revenue"].id,
                    "amount_currency": -500.0,
                    "balance": -500.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.remove_reconciled_line(st_line.line_ids[-1].id)
        self.assertEqual(
            st_line.line_ids[-1].reconcile_model_id,
            reco_model,
            "The test reco model should be assigned on the new suspense line",
        )

    def test_delete_lines_with_different_reco_model(self):
        reco_model1 = self.env["account.reconcile.model"].create(
            {
                "name": "Test reco model",
                "match_journal_ids": [
                    Command.set([self.company_data["default_journal_bank"].id])
                ],
                "match_label": "contains",
                "match_label_param": "blblbl",
                "line_ids": [
                    Command.create(
                        {"account_id": self.company_data["default_account_revenue"].id}
                    )
                ],
            }
        )
        reco_model2 = reco_model1.copy()
        st_line = self._create_st_line(
            1000.0,
            date="2025-08-06",
            payment_ref="blblbl",
            partner_id=self.partner_a.id,
            update_create_date=False,
        )

        reco_model1._trigger_reconciliation_model(st_line)
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id, {"balance": -500, "amount_currency": -500}
        )
        reco_model2._trigger_reconciliation_model(st_line)

        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "balance": 1000.0,
                    "reconciled": False,
                    "reconcile_model_id": False,
                },
                {
                    "account_id": self.company_data["default_account_revenue"].id,
                    "amount_currency": -500.0,
                    "balance": -500.0,
                    "reconciled": False,
                    "reconcile_model_id": reco_model1.id,
                },
                {
                    "account_id": self.company_data["default_account_revenue"].id,
                    "amount_currency": -500.0,
                    "balance": -500.0,
                    "reconciled": False,
                    "reconcile_model_id": reco_model2.id,
                },
            ],
        )

        st_line.remove_reconciled_line(st_line.line_ids[-1].id)

        self.assertEqual(
            st_line.line_ids[-1].reconcile_model_id.id,
            reco_model2.id,
            "The reco model from the deleted line should be assigned on the new suspense line",
        )

    def test_account_default_taxes_of_reco_model(self):
        reco_model = self.env["account.reconcile.model"].create(
            {
                "name": "test reco model",
                "line_ids": [
                    Command.create({"account_id": self.default_tax_account.id})
                ],
            }
        )
        st_line = self._create_st_line(100.0, update_create_date=False)
        reco_model._trigger_reconciliation_model(st_line)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )

    def test_add_default_tax_of_account_with_set_account(self):
        st_line = self._create_st_line(200.0, update_create_date=False)
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.default_tax_account.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -190.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_invoice_foreign_currency_lost_precision_case(self):
        self.env["ir.config_parameter"].set_param(
            "account.bank_rec_payment_tolerance", "0.03"
        )
        currency_brasilian_real = self.setup_other_currency(
            "BRL", rounding=0.01, rates=[("2017-01-01", 5.421327349)]
        )
        receivable_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 143.62}],
            currency_id=currency_brasilian_real.id,
        )
        self.assertEqual(receivable_line.balance, 26.49)
        st_line = self._create_st_line(amount=26.05)
        st_line.set_line_bank_statement_line(receivable_line.ids)
        exchange_diff_account = (
            self.env.company.account_config_id.income_currency_exchange_account_id
        )
        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, exchange_diff_account.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 26.05,
                    "currency_id": self.company_data["currency"].id,
                    "reconciled": False,
                },
                {
                    "account_id": self.partner_a.property_account_receivable_id.id,
                    "amount_currency": -143.62,
                    "currency_id": currency_brasilian_real.id,
                    "reconciled": True,
                },
                {
                    "account_id": exchange_diff_account.id,
                    "amount_currency": 0.44,
                    "currency_id": self.company_data["currency"].id,
                    "reconciled": False,
                },
            ],
        )
        self.assertTrue(
            receivable_line.reconciled,
            "The invoice should have been marked as reconciled",
        )

    def test_reconcile_invoice_with_bank_statement_line(self):
        foreign_curr = self.setup_other_currency(
            "EUR",
            rates=[
                ("2019-06-28", 2.0),
                ("2019-06-24", 3.0),
            ],
        )
        invoice = self._create_invoice_line(
            move_type="out_invoice",
            invoice_date="2019-06-24",
            currency_id=foreign_curr.id,
            invoice_line_ids=[{"price_unit": 6000.0}],
        ).move_id
        invoice_rec_line = invoice.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )
        statement_line = self._create_st_line(
            amount=2000,
            amount_currency=1000,
            foreign_currency_id=foreign_curr.id,
            journal_id=self.company_data["default_journal_bank"].id,
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        statement_line_rec_line = statement_line.move_id.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_cash"
        )

        invoice.invalidate_recordset(["invoice_outstanding_credits_debits_widget"])
        widget_vals = invoice.invoice_outstanding_credits_debits_widget

        if widget_vals:
            current_amounts = {
                vals["move_id"]: vals["amount"] for vals in widget_vals["content"]
            }
        else:
            current_amounts = {}
        self.assertDictEqual(
            current_amounts,
            {
                statement_line.move_id.id: 1000.0,
            },
        )
        invoice.js_add_outstanding_line(statement_line_rec_line.id)
        statement_line_rec_line = statement_line.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )[0]
        partials = (
            invoice_rec_line.matched_debit_ids
            | invoice_rec_line.matched_credit_ids
            | statement_line_rec_line.matched_debit_ids
            | statement_line_rec_line.matched_credit_ids
        ).sorted()

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 333.33,
                    "debit_amount_currency": 1000.0,
                    "credit_amount_currency": 1000.0,
                    "debit_move_id": invoice_rec_line.id,
                    "credit_move_id": statement_line_rec_line.id,
                },
                {
                    "amount": 1666.67,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": statement_line_rec_line.id,
                },
            ],
        )

        self.assertRecordValues(
            invoice_rec_line + statement_line_rec_line,
            [
                {
                    "amount_residual": 1666.67,
                    "amount_residual_currency": 5000,
                    "reconciled": False,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

        self.assert_invoice_outstanding_reconciled_widget(
            invoice,
            {
                statement_line.move_id.id: 1000.0,
                partials.exchange_move_id.id: 1666.67,
            },
        )
        counterpart_line_id = statement_line.line_ids[-1].id
        statement_line.set_account_bank_statement_line(
            counterpart_line_id,
            self.env.company.account_config_id.account_journal_suspense_account_id.id,
        )
        invoice.invalidate_recordset(["invoice_outstanding_credits_debits_widget"])
        self.assertTrue(
            invoice.invoice_outstanding_credits_debits_widget,
            "a statement line whose counterpart is still on the suspense account is "
            "the case the widget exists to offer",
        )

        statement_line.set_account_bank_statement_line(
            counterpart_line_id,
            self.company_data["default_account_revenue"].id,
        )
        invoice.invalidate_recordset(["invoice_outstanding_credits_debits_widget"])
        self.assertFalse(
            invoice.invoice_outstanding_credits_debits_widget,
            "Only statement lines with suspense account should be considered",
        )

    def test_reconcile_bill_with_account_default_tax(self):
        tax = self.env["account.tax"].create(
            {
                "name": "10% tax",
                "amount_type": "percent",
                "amount": 10.0,
                "type_tax_use": "purchase",
            }
        )
        self.default_tax_account.tax_ids = tax
        bill = self._create_invoice_line(
            move_type="in_invoice",
            invoice_date="2019-06-24",
            invoice_line_ids=[{"price_unit": 2000.00, "tax_ids": tax.ids}],
        ).move_id
        bill_rec_line = bill.line_ids.filtered(
            lambda x: x.account_id.account_type == "liability_payable"
        )
        statement_line = self._create_st_line(
            amount=-2530, partner_id=self.partner_a.id
        )
        statement_line.set_line_bank_statement_line(bill_rec_line.ids)
        statement_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            statement_line.line_ids[-1].id, self.default_tax_account.id
        )

        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": -2530.00,
                    "reconciled": False,
                    "reconciled_lines_ids": [],
                },
                {
                    "account_id": bill_rec_line.account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 2200.00,
                    "reconciled": True,
                    "reconciled_lines_ids": bill_rec_line.ids,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": tax.ids,
                    "tax_line_id": False,
                    "balance": 300,
                    "reconciled": False,
                    "reconciled_lines_ids": [],
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": tax.id,
                    "balance": 30,
                    "reconciled": False,
                    "reconciled_lines_ids": [],
                },
            ],
        )

    def test_reconcile_refund_with_bank_statement_line(self):
        foreign_curr = self.setup_other_currency(
            "EUR",
            rates=[
                ("2019-06-28", 2.0),
                ("2019-06-24", 3.0),
            ],
        )
        refund = self._create_invoice_line(
            move_type="in_invoice",
            invoice_date="2019-06-24",
            currency_id=foreign_curr.id,
            invoice_line_ids=[{"price_unit": 6000.0}],
        ).move_id
        refund_rec_line = refund.line_ids.filtered(
            lambda x: x.account_id.account_type == "liability_payable"
        )
        statement_line = self._create_st_line(
            amount=-2000,
            date="2019-06-28",
            journal_id=self.company_data["default_journal_bank"].id,
            partner_id=self.partner_a.id,
            update_create_date=False,
        )
        statement_line_rec_line = statement_line.move_id.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_cash"
        )

        refund.invalidate_recordset(["invoice_outstanding_credits_debits_widget"])
        widget_vals = refund.invoice_outstanding_credits_debits_widget

        if widget_vals:
            current_amounts = {
                vals["move_id"]: vals["amount"] for vals in widget_vals["content"]
            }
        else:
            current_amounts = {}
        self.assertDictEqual(
            current_amounts,
            {
                statement_line.move_id.id: 4000.0,
            },
        )

        refund.js_add_outstanding_line(statement_line_rec_line.id)
        statement_line_rec_line = statement_line.line_ids.filtered(
            lambda x: x.account_id.account_type == "liability_payable"
        )[0]
        partials = (
            refund_rec_line.matched_debit_ids
            | refund_rec_line.matched_credit_ids
            | statement_line_rec_line.matched_debit_ids
            | statement_line_rec_line.matched_credit_ids
        ).sorted()

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 1333.33,
                    "debit_amount_currency": 3999.99,
                    "credit_amount_currency": 3999.99,
                    "credit_move_id": refund_rec_line.id,
                    "debit_move_id": statement_line_rec_line.id,
                },
                {
                    "amount": 666.67,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "debit_move_id": statement_line_rec_line.id,
                },
            ],
        )

        self.assertRecordValues(
            refund_rec_line + statement_line_rec_line,
            [
                {
                    "amount_residual": -666.67,
                    "amount_residual_currency": -2000.01,
                    "reconciled": False,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

        self.assert_invoice_outstanding_reconciled_widget(
            refund,
            {
                statement_line.move_id.id: 3999.99,
                partials.exchange_move_id.id: 666.67,
            },
        )

    def test_currency_rate_with_cron(self):
        company_2 = self.company_data_2["company"]
        company_2.currency_id = self.other_currency
        new_journal = self.company_data_2["default_journal_bank"]
        new_journal.currency_id = self.other_currency
        new_journal.inbound_payment_channel_ids.payment_account_id = (
            self.inbound_payment_channel.payment_account_id.copy(
                {"company_ids": [Command.link(company_2.id)]}
            )
        )

        payment = self._create_and_post_payment(
            amount=100,
            memo="INV/24-25/0001 - pay_AretqwwXerereE",
            journal_id=new_journal.id,
            company_id=company_2.id,
            currency_id=self.company_data["currency"].id,
        )
        st_line = self._create_st_line(
            amount=1000,
            payment_ref="pay_AretqwwXerereE",
            update_create_date=False,
            journal_id=new_journal.id,
            company_id=company_2.id,
        )
        st_line.set_line_bank_statement_line(
            payment.move_id.line_ids.filtered(
                lambda l: l.account_id == payment.outstanding_account_id
            ).ids
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "amount_currency": 1000.0,
                    "currency_id": self.other_currency.id,
                    "balance": 1000.0,
                    "reconciled": False,
                },
                {
                    "account_id": payment.outstanding_account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "amount_currency": -900.0,
                    "currency_id": self.other_currency.id,
                    "balance": -900.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_payment_widget_vals_partials(self):
        foreign_curr = self.setup_other_currency(
            "EUR",
            rates=[
                ("2019-06-28", 2.0),
            ],
        )
        foreign_currency_journal = self.company_data["default_journal_bank"].copy(
            {"currency_id": foreign_curr.id}
        )
        statement_line = self.env["account.bank.statement.line"].create(
            {
                "name": "test_statement",
                "date": "2019-06-28",
                "payment_ref": "line_1",
                "partner_id": self.partner_a.id,
                "journal_id": foreign_currency_journal.id,
                "amount": 400.0,
            }
        )
        statement_line_rec_line = statement_line.move_id.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_cash"
        )
        invoice_1 = self.init_invoice(
            move_type="out_invoice",
            invoice_date="2019-06-24",
            amounts=[100],
            partner=self.partner_a,
            post=True,
        )
        invoice_2 = self.init_invoice(
            move_type="out_invoice",
            invoice_date="2019-06-24",
            amounts=[100],
            partner=self.partner_a,
            post=True,
        )

        invoice_1.js_add_outstanding_line(statement_line_rec_line.id)

        self.assert_invoice_outstanding_to_reconcile_widget(
            invoice_2,
            {
                statement_line.move_id.id: 100.0,
            },
        )
        invoice_2.js_add_outstanding_line(statement_line_rec_line.id)

        invoice_3 = self.init_invoice(
            move_type="out_invoice",
            invoice_date="2019-06-24",
            amounts=[100],
            partner=self.partner_a,
            post=True,
        )
        self.assert_invoice_outstanding_to_reconcile_widget(invoice_3, {})

        partial_id = invoice_1._get_all_reconciled_invoice_partials()[0].get(
            "partial_id"
        )
        statement_line_rec_line.move_id.js_remove_outstanding_partial(partial_id)

        self.assert_invoice_outstanding_to_reconcile_widget(
            invoice_1,
            {
                statement_line.move_id.id: 100.0,
            },
        )

        self.assert_invoice_outstanding_reconciled_widget(
            invoice_2,
            {
                statement_line.move_id.id: 100,
            },
        )

    def test_remove_partner_from_set_account_line(self):
        st_line = self._create_st_line(
            100.0, update_create_date=False, partner_id=self.partner_a.id
        )
        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "partner_id": self.partner_a.id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": self.partner_a.id,
                    "balance": -100.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id, {"balance": -20, "amount_currency": -20}
        )
        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id, {"balance": -20, "amount_currency": -20}
        )
        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "partner_id": self.partner_a.id,
                    "balance": 100.0,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": self.partner_a.id,
                    "balance": -20.0,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": self.partner_a.id,
                    "balance": -20.0,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": self.partner_a.id,
                    "balance": -60.0,
                },
            ],
        )
        st_line.edit_reconcile_line(st_line.line_ids[-1].id, {"partner_id": False})
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "partner_id": self.partner_a.id,
                    "balance": 100.0,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": self.partner_a.id,
                    "balance": -20.0,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": self.partner_a.id,
                    "balance": -20.0,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": False,
                    "balance": -60.0,
                },
            ],
        )
        st_line.edit_reconcile_line(st_line.line_ids[2].id, {"partner_id": False})
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "partner_id": self.partner_a.id,
                    "balance": 100.0,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": self.partner_a.id,
                    "balance": -20.0,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": False,
                    "balance": -60.0,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "partner_id": False,
                    "balance": -20.0,
                },
            ],
        )

    def test_analytic_distribution_for_early_payment_statement(self):
        early_payment_term = self.env["account.payment.term"].create(
            {
                "name": "early_payment_term",
                "company_id": self.company_data["company"].id,
                "early_pay_discount_computation": "included",
                "early_discount": True,
                "discount_percentage": 2,
                "discount_days": 7,
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100.0,
                            "nb_days": 30,
                        }
                    ),
                ],
            }
        )

        analytic_plan = self.env["account.analytic.plan"].create(
            {
                "name": "existential plan",
            }
        )
        analytic_account = self.env["account.analytic.account"].create(
            {
                "name": "positive_account",
                "plan_id": analytic_plan.id,
            }
        )

        cash_discount_account = self.company_data[
            "company"
        ].account_config_id.account_journal_early_pay_discount_loss_account_id
        self.env["account.analytic.distribution.model"].create(
            {
                "account_prefix": cash_discount_account.code,
                "analytic_distribution": {analytic_account.id: 100.0},
            }
        )

        invoice = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "date": "2017-01-01",
                    "invoice_date": "2017-01-01",
                    "invoice_payment_term_id": early_payment_term.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "line",
                                "price_unit": 100.0,
                            }
                        )
                    ],
                }
            ]
        )
        invoice.action_post()

        statement = self.env["account.bank.statement.line"].create(
            {
                "date": "2017-01-01",
                "payment_ref": invoice.payment_reference,
                "partner_id": self.partner_b.id,
                "amount": 98.0,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        receivable_line = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type == "asset_receivable"
        )
        statement.set_line_bank_statement_line(receivable_line.ids)

        early_payment_line = statement.line_ids.filtered(lambda p: p.balance == 2.0)
        self.assertTrue(early_payment_line.analytic_distribution)

    def test_edit_account_id_analytic(self):
        analytic_plan = self.env["account.analytic.plan"].create({"name": "Plan Test"})
        analytic_account_1 = self.env["account.analytic.account"].create(
            {
                "name": "analytic_account_1",
                "plan_id": analytic_plan.id,
            }
        )
        analytic_distribution = self.env["account.analytic.distribution.model"].create(
            {
                "analytic_distribution": {analytic_account_1.id: 100},
            }
        )
        account = self.env["account.account"].create(
            {
                "name": "test account",
                "code": "60001",
                "account_type": "expense",
            }
        )
        st_line = self._create_st_line(amount=100, update_create_date=False)
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id,
            {
                "analytic_distribution": analytic_distribution.analytic_distribution,
            },
        )
        old_analytic_line = st_line.line_ids[1].analytic_line_ids
        self.assertEqual(len(old_analytic_line), 1)
        self.assertTrue(old_analytic_line)
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id,
            {
                "account_id": account.id,
            },
        )
        self.assertNotEqual(old_analytic_line, st_line.line_ids[1].analytic_line_ids)
        self.assertEqual(len(st_line.line_ids[1].analytic_line_ids), 1)

    def test_reconciliation_without_payment_account(self):
        self.company_data[
            "default_journal_bank"
        ].inbound_payment_channel_ids.payment_account_id = False
        self.company_data[
            "default_journal_bank"
        ].outbound_payment_channel_ids.payment_account_id = False
        self._create_and_post_payment(amount=100)
        statement_line = self._create_st_line(amount=100, update_create_date=False)
        statement_line._try_auto_reconcile_statement_lines()
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": self.company_data[
                        "default_journal_bank"
                    ].default_account_id.id,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.company_data[
                        "default_journal_bank"
                    ].suspense_account_id.id,
                    "balance": -100.0,
                    "reconciled": False,
                },
            ],
        )

    def test_set_account_then_edit_with_taxes(self):
        st_line = self._create_st_line(200.0, update_create_date=False)
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )

        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id,
            {
                "tax_ids": [Command.link(self.default_tax.id)],
            },
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -190.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )

    def test_delete_line_with_taxes(self):
        st_line = self._create_st_line(200.0, update_create_date=False)
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.default_tax_account.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -190.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.remove_reconciled_line(st_line.line_ids[-2].id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": -200.0,
                    "reconciled": False,
                },
            ],
        )

    def test_delete_line_with_taxes_with_multiple_lines(self):
        st_line = self._create_st_line(200.0, update_create_date=False)
        self.default_tax_account.tax_ids = False
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.default_tax_account.id
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id,
            {
                "balance": -100,
                "amount_currency": -100,
                "tax_ids": [Command.link(self.default_tax.id)],
            },
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": -100.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.default_tax_account.id
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id, {"tax_ids": [Command.link(self.default_tax.id)]}
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -20.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.remove_reconciled_line(st_line.line_ids[-2].id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": -100.0,
                    "reconciled": False,
                },
            ],
        )

    def test_set_account_then_edit_remove_taxes(self):
        st_line = self._create_st_line(200.0, update_create_date=False)
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.default_tax_account.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -190.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[-2].id, {"tax_ids": [Command.unlink(self.default_tax.id)]}
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": -200.0,
                    "reconciled": False,
                },
            ],
        )

    def test_set_account_then_edit_multiple_taxes(self):
        new_tax = self.env["account.tax"].create(
            {
                "name": "new_tax",
                "amount_type": "fixed",
                "amount": 20.0,
            }
        )
        st_line = self._create_st_line(200.0, update_create_date=False)
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.default_tax_account.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -190.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[-2].id, {"tax_ids": [Command.link(new_tax.id)]}
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": (self.default_tax + new_tax).ids,
                    "tax_line_id": False,
                    "balance": -170.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": new_tax.id,
                    "balance": -20.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )

    def test_set_account_multiple_taxes_delete_line(self):
        new_tax = self.env["account.tax"].create(
            {
                "name": "new_tax",
                "amount_type": "fixed",
                "amount": 20.0,
            }
        )
        self.default_tax_account.tax_ids = [
            Command.set((self.default_tax + new_tax).ids)
        ]
        st_line = self._create_st_line(200.0, update_create_date=False)
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.default_tax_account.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": (self.default_tax + new_tax).ids,
                    "tax_line_id": False,
                    "balance": -170.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": new_tax.id,
                    "balance": -20.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[1].id, {"tax_ids": [Command.unlink(self.default_tax.id)]}
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": new_tax.ids,
                    "tax_line_id": False,
                    "balance": -180.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": new_tax.id,
                    "balance": -20.0,
                    "reconciled": False,
                },
            ],
        )

    def test_set_account_then_edit_remove_taxes_and_add_new_tax(self):
        new_tax = self.env["account.tax"].create(
            {
                "name": "new_tax",
                "amount_type": "fixed",
                "amount": 20.0,
            }
        )
        st_line = self._create_st_line(200.0, update_create_date=False)
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.default_tax_account.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -190.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[1].id,
            {
                "tax_ids": [
                    Command.unlink(self.default_tax.id),
                    Command.set(new_tax.ids),
                ]
            },
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": new_tax.ids,
                    "tax_line_id": False,
                    "balance": -180.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": new_tax.id,
                    "balance": -20.0,
                    "reconciled": False,
                },
            ],
        )

    def test_set_account_then_edit_remove_taxes_and_add_new_taxes(self):
        new_tax = self.env["account.tax"].create(
            {
                "name": "new_tax",
                "amount_type": "fixed",
                "amount": 20.0,
            }
        )
        st_line = self._create_st_line(200.0, update_create_date=False)
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.default_tax_account.id
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": self.default_tax.ids,
                    "tax_line_id": False,
                    "balance": -190.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[1].id,
            {
                "tax_ids": [
                    Command.unlink(self.default_tax.id),
                    Command.set((new_tax + self.default_tax).ids),
                ]
            },
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": (self.default_tax + new_tax).ids,
                    "tax_line_id": False,
                    "balance": -170.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": new_tax.id,
                    "balance": -20.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.default_tax_account.id,
                    "tax_ids": [],
                    "tax_line_id": self.default_tax.id,
                    "balance": -10.0,
                    "reconciled": False,
                },
            ],
        )

    def test_multiple_tax_with_different_types(self):
        sale_tax = self.env["account.tax"].create(
            {
                "name": "10% S",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        purchase_tax = self.env["account.tax"].create(
            {
                "name": "10% P",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
            }
        )
        st_line = self._create_st_line(100.0, update_create_date=False)
        st_line.with_context(
            account_default_taxes=True
        ).set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )

        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id,
            {
                "tax_ids": [Command.link(purchase_tax.id), Command.link(sale_tax.id)],
            },
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "tax_ids": (purchase_tax + sale_tax).ids,
                    "tax_line_id": False,
                    "balance": -83.34,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "tax_ids": [],
                    "tax_line_id": sale_tax.id,
                    "balance": -8.33,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "tax_ids": [],
                    "tax_line_id": purchase_tax.id,
                    "balance": -8.33,
                    "reconciled": False,
                },
            ],
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[1].id,
            {
                "tax_ids": [Command.unlink(purchase_tax.id)],
            },
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 100.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "tax_ids": sale_tax.ids,
                    "tax_line_id": False,
                    "balance": -90.91,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "tax_ids": [],
                    "tax_line_id": sale_tax.id,
                    "balance": -9.09,
                    "reconciled": False,
                },
            ],
        )

    def test_upload_xml(self):
        xml = b"""<?xml version='1.0' encoding='UTF-8'?>
        <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
            <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
            <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
            <cbc:ID>INV/2023/00009</cbc:ID>
            <cbc:IssueDate>2023-06-20</cbc:IssueDate>
            <cbc:DueDate>2023-06-20</cbc:DueDate>
            <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
            <cbc:Note>Terms and condition</cbc:Note>
            <cbc:DocumentCurrencyCode>USD</cbc:DocumentCurrencyCode>
            <cac:OrderReference>
                <cbc:ID>DOEO</cbc:ID>
            </cac:OrderReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>INV_2023_00009.pdf</cbc:ID>
            </cac:AdditionalDocumentReference>
            <cac:AccountingSupplierParty>
            <cac:Party>
                <cbc:EndpointID schemeID="9925">BE0246697724</cbc:EndpointID>
                <cac:PartyName>
                    <cbc:Name>BE Company CoA</cbc:Name>
                </cac:PartyName>
                <cac:PostalAddress>
                    <cbc:StreetName>1021 Sint-Bernardsesteenweg</cbc:StreetName>
                    <cbc:CityName>Antwerpen</cbc:CityName>
                    <cbc:PostalZone>2660</cbc:PostalZone>
                    <cac:Country>
                    <cbc:IdentificationCode>BE</cbc:IdentificationCode>
                    </cac:Country>
                </cac:PostalAddress>
                <cac:PartyTaxScheme>
                    <cbc:CompanyID>BE0246697724</cbc:CompanyID>
                    <cac:TaxScheme>
                        <cbc:ID>VAT</cbc:ID>
                    </cac:TaxScheme>
                </cac:PartyTaxScheme>
                <cac:PartyLegalEntity>
                    <cbc:RegistrationName>BE Company CoA</cbc:RegistrationName>
                    <cbc:CompanyID>BE0246697724</cbc:CompanyID>
                </cac:PartyLegalEntity>
                <cac:Contact>
                    <cbc:Name>BE Company CoA</cbc:Name>
                    <cbc:Telephone>+32 470 12 34 56</cbc:Telephone>
                    <cbc:ElectronicMail>info@company.beexample.com</cbc:ElectronicMail>
                  </cac:Contact>
                </cac:Party>
            </cac:AccountingSupplierParty>
            <cac:AccountingCustomerParty>
                <cac:Party>
                    <cbc:EndpointID schemeID="9925">BE0665978937</cbc:EndpointID>
                    <cac:PartyName>
                        <cbc:Name>Proximus</cbc:Name>
                    </cac:PartyName>
                    <cac:PostalAddress>
                        <cac:Country>
                            <cbc:IdentificationCode>BE</cbc:IdentificationCode>
                        </cac:Country>
                    </cac:PostalAddress>
                    <cac:PartyTaxScheme>
                        <cbc:CompanyID>BE0665978937</cbc:CompanyID>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:PartyTaxScheme>
                    <cac:PartyLegalEntity>
                        <cbc:RegistrationName>Proximus</cbc:RegistrationName>
                        <cbc:CompanyID>BE0665978937</cbc:CompanyID>
                    </cac:PartyLegalEntity>
                    <cac:Contact>
                        <cbc:Name>Proximus</cbc:Name>
                    </cac:Contact>
                </cac:Party>
            </cac:AccountingCustomerParty>
            <cac:Delivery>
                <cac:DeliveryLocation>
                    <cac:Address>
                        <cac:Country>
                            <cbc:IdentificationCode>BE</cbc:IdentificationCode>
                        </cac:Country>
                    </cac:Address>
                </cac:DeliveryLocation>
            </cac:Delivery>
            <cac:PaymentMeans>
                <cbc:PaymentMeansCode name="credit transfer">30</cbc:PaymentMeansCode>
                <cbc:PaymentID>+++000/0000/22329+++</cbc:PaymentID>
                <cac:PayeeFinancialAccount>
                    <cbc:ID>BE83957821438115</cbc:ID>
                </cac:PayeeFinancialAccount>
            </cac:PaymentMeans>
            <cac:LegalMonetaryTotal>
                <cbc:LineExtensionAmount currencyID="USD">100.00</cbc:LineExtensionAmount>
                <cbc:TaxExclusiveAmount currencyID="USD">100.00</cbc:TaxExclusiveAmount>
                <cbc:TaxInclusiveAmount currencyID="USD">100.00</cbc:TaxInclusiveAmount>
                <cbc:PrepaidAmount currencyID="USD">0.00</cbc:PrepaidAmount>
                <cbc:PayableAmount currencyID="USD">100.00</cbc:PayableAmount>
            </cac:LegalMonetaryTotal>
            <cac:InvoiceLine>
                <cbc:ID>984</cbc:ID>
                <cbc:InvoicedQuantity unitCode="C62">1.0</cbc:InvoicedQuantity>
                <cbc:LineExtensionAmount currencyID="USD">100.00</cbc:LineExtensionAmount>
                <cac:Item>
                    <cbc:Description>[FURN_6666] Acoustic Bloc Screens</cbc:Description>
                    <cbc:Name>Acoustic Bloc Screens</cbc:Name>
                    <cac:SellersItemIdentification>
                        <cbc:ID>FURN_6666</cbc:ID>
                    </cac:SellersItemIdentification>
                    <cac:ClassifiedTaxCategory>
                        <cbc:ID>S</cbc:ID>
                        <cbc:Percent>21.0</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:ClassifiedTaxCategory>
                </cac:Item>
                <cac:Price>
                    <cbc:PriceAmount currencyID="USD">100.00</cbc:PriceAmount>
                </cac:Price>
            </cac:InvoiceLine>
        </Invoice>
        """

        statement_line = self._create_st_line(amount=-100, update_create_date=False)
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test_file",
                "mimetype": "text/xml",
                "datas": base64.b64encode(xml),
            }
        )
        self.env["account.bank.statement.line"].with_context(
            statement_line_id=statement_line.id
        ).create_document_from_attachment(attachment.ids)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": self.company_data[
                        "default_journal_bank"
                    ].default_account_id.id,
                    "balance": -100.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.company_data["default_account_payable"].id,
                    "balance": 100.0,
                    "reconciled": True,
                },
            ],
        )

    def test_auto_activate_currency_with_xml_file(self):
        xml = b"""<?xml version='1.0' encoding='UTF-8'?>
        <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
            <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
            <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
            <cbc:ID>INV/2023/00009</cbc:ID>
            <cbc:IssueDate>2023-06-20</cbc:IssueDate>
            <cbc:DueDate>2023-06-20</cbc:DueDate>
            <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
            <cbc:Note>Terms and condition</cbc:Note>
            <cbc:DocumentCurrencyCode>INR</cbc:DocumentCurrencyCode>
            <cac:OrderReference>
                <cbc:ID>DOEO</cbc:ID>
            </cac:OrderReference>
            <cac:AdditionalDocumentReference>
                <cbc:ID>INV_2023_00009.pdf</cbc:ID>
            </cac:AdditionalDocumentReference>
            <cac:AccountingSupplierParty>
            <cac:Party>
                <cbc:EndpointID schemeID="9925">BE0246697724</cbc:EndpointID>
                <cac:PartyName>
                    <cbc:Name>BE Company CoA</cbc:Name>
                </cac:PartyName>
                <cac:PostalAddress>
                    <cbc:StreetName>1021 Sint-Bernardsesteenweg</cbc:StreetName>
                    <cbc:CityName>Antwerpen</cbc:CityName>
                    <cbc:PostalZone>2660</cbc:PostalZone>
                    <cac:Country>
                    <cbc:IdentificationCode>BE</cbc:IdentificationCode>
                    </cac:Country>
                </cac:PostalAddress>
                <cac:PartyTaxScheme>
                    <cbc:CompanyID>BE0246697724</cbc:CompanyID>
                    <cac:TaxScheme>
                        <cbc:ID>VAT</cbc:ID>
                    </cac:TaxScheme>
                </cac:PartyTaxScheme>
                <cac:PartyLegalEntity>
                    <cbc:RegistrationName>BE Company CoA</cbc:RegistrationName>
                    <cbc:CompanyID>BE0246697724</cbc:CompanyID>
                </cac:PartyLegalEntity>
                <cac:Contact>
                    <cbc:Name>BE Company CoA</cbc:Name>
                    <cbc:Telephone>+32 470 12 34 56</cbc:Telephone>
                    <cbc:ElectronicMail>info@company.beexample.com</cbc:ElectronicMail>
                  </cac:Contact>
                </cac:Party>
            </cac:AccountingSupplierParty>
            <cac:AccountingCustomerParty>
                <cac:Party>
                    <cbc:EndpointID schemeID="9925">BE0665978937</cbc:EndpointID>
                    <cac:PartyName>
                        <cbc:Name>Proximus</cbc:Name>
                    </cac:PartyName>
                    <cac:PostalAddress>
                        <cac:Country>
                            <cbc:IdentificationCode>BE</cbc:IdentificationCode>
                        </cac:Country>
                    </cac:PostalAddress>
                    <cac:PartyTaxScheme>
                        <cbc:CompanyID>BE0665978937</cbc:CompanyID>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:PartyTaxScheme>
                    <cac:PartyLegalEntity>
                        <cbc:RegistrationName>Proximus</cbc:RegistrationName>
                        <cbc:CompanyID>BE0665978937</cbc:CompanyID>
                    </cac:PartyLegalEntity>
                    <cac:Contact>
                        <cbc:Name>Proximus</cbc:Name>
                    </cac:Contact>
                </cac:Party>
            </cac:AccountingCustomerParty>
            <cac:Delivery>
                <cac:DeliveryLocation>
                    <cac:Address>
                        <cac:Country>
                            <cbc:IdentificationCode>BE</cbc:IdentificationCode>
                        </cac:Country>
                    </cac:Address>
                </cac:DeliveryLocation>
            </cac:Delivery>
            <cac:PaymentMeans>
                <cbc:PaymentMeansCode name="credit transfer">30</cbc:PaymentMeansCode>
                <cbc:PaymentID>+++000/0000/22329+++</cbc:PaymentID>
                <cac:PayeeFinancialAccount>
                    <cbc:ID>BE83957821438115</cbc:ID>
                </cac:PayeeFinancialAccount>
            </cac:PaymentMeans>
            <cac:LegalMonetaryTotal>
                <cbc:LineExtensionAmount currencyID="INR">100.00</cbc:LineExtensionAmount>
                <cbc:TaxExclusiveAmount currencyID="INR">100.00</cbc:TaxExclusiveAmount>
                <cbc:TaxInclusiveAmount currencyID="INR">100.00</cbc:TaxInclusiveAmount>
                <cbc:PrepaidAmount currencyID="INR">0.00</cbc:PrepaidAmount>
                <cbc:PayableAmount currencyID="INR">100.00</cbc:PayableAmount>
            </cac:LegalMonetaryTotal>
            <cac:InvoiceLine>
                <cbc:ID>984</cbc:ID>
                <cbc:InvoicedQuantity unitCode="C62">1.0</cbc:InvoicedQuantity>
                <cbc:LineExtensionAmount currencyID="INR">100.00</cbc:LineExtensionAmount>
                <cac:Item>
                    <cbc:Description>[FURN_6666] Acoustic Bloc Screens</cbc:Description>
                    <cbc:Name>Acoustic Bloc Screens</cbc:Name>
                    <cac:SellersItemIdentification>
                        <cbc:ID>FURN_6666</cbc:ID>
                    </cac:SellersItemIdentification>
                    <cac:ClassifiedTaxCategory>
                        <cbc:ID>S</cbc:ID>
                        <cbc:Percent>21.0</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:ClassifiedTaxCategory>
                </cac:Item>
                <cac:Price>
                    <cbc:PriceAmount currencyID="INR">100.00</cbc:PriceAmount>
                </cac:Price>
            </cac:InvoiceLine>
        </Invoice>
        """
        statement_line = self._create_st_line(amount=-100, update_create_date=False)
        attachment = self.env["ir.attachment"].create(
            {
                "name": "test_file",
                "mimetype": "text/xml",
                "datas": base64.b64encode(xml),
            }
        )
        test_currency = self.setup_other_currency(
            "INR", rates=[("2025-01-01", 1.00)], active=False
        )
        self.assertFalse(test_currency.active)
        self.env["account.bank.statement.line"].with_context(
            statement_line_id=statement_line.id,
        ).create_document_from_attachment(attachment.ids)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": self.company_data[
                        "default_journal_bank"
                    ].default_account_id.id,
                    "balance": -100.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.company_data["default_account_payable"].id,
                    "balance": 100.0,
                    "reconciled": True,
                },
            ],
        )
        self.assertTrue(test_currency.active)

    def test_reconciliation_with_payment_terms(self):
        payment_term = self.env["account.payment.term"].create(
            {
                "name": "Test payment term",
                "company_id": self.company_data["company"].id,
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": amount,
                            "nb_days": nb_days,
                        }
                    )
                    for amount, nb_days in [(33.33, 0), (33.33, 30), (33.34, 60)]
                ],
            }
        )

        payment_term_2 = self.env["account.payment.term"].create(
            {
                "name": "Test payment term",
                "company_id": self.company_data["company"].id,
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": amount,
                            "nb_days": nb_days,
                        }
                    )
                    for amount, nb_days in [(50.0, 0), (50.0, 30)]
                ],
            }
        )
        suspense_account = self.company_data["default_journal_bank"].suspense_account_id

        statement_line = self._create_st_line(amount=-90, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "in_invoice", invoice_line_ids=[{"price_unit": 200.0}]
        )
        statement_line.set_line_bank_statement_line(move_line_1.ids)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": -90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 90.0,
                    "reconciled": True,
                },
            ],
        )

        statement_line = self._create_st_line(amount=-90, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "in_invoice",
            invoice_payment_term_id=payment_term_2.id,
            invoice_line_ids=[{"price_unit": 200.0}],
        )
        statement_line.set_line_bank_statement_line(move_line_1.ids)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": -90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": True,
                },
                {
                    "account_id": suspense_account.id,
                    "amount_currency": -110.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -110.0,
                    "reconciled": False,
                },
            ],
        )
        statement_line = self._create_st_line(amount=-90, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "in_invoice",
            invoice_payment_term_id=payment_term_2.id,
            invoice_line_ids=[{"price_unit": 200.0}],
        )
        move_line_1.move_id.js_add_outstanding_line(statement_line.line_ids[0].id)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": -90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 90.0,
                    "reconciled": True,
                },
            ],
        )
        statement_line = self._create_st_line(amount=-100, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "in_invoice",
            invoice_payment_term_id=payment_term_2.id,
            invoice_line_ids=[{"price_unit": 200.0}],
        )
        move_line_1.move_id.js_add_outstanding_line(statement_line.line_ids[0].id)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": -100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -100.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 100.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 100.0,
                    "reconciled": True,
                },
            ],
        )

        statement_line = self._create_st_line(amount=-90, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "in_invoice",
            invoice_payment_term_id=payment_term.id,
            invoice_line_ids=[{"price_unit": 200.0}],
        )
        statement_line.set_line_bank_statement_line(move_line_1.ids)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": -90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 66.66,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 66.66,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 66.68,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 66.68,
                    "reconciled": True,
                },
                {
                    "account_id": suspense_account.id,
                    "amount_currency": -110.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -110.0,
                    "reconciled": False,
                },
            ],
        )
        statement_line = self._create_st_line(amount=-90, update_create_date=False)
        move_line_1 = self._create_invoice_line(
            "in_invoice",
            invoice_payment_term_id=payment_term.id,
            invoice_line_ids=[{"price_unit": 200.0}],
        )
        move_line_1.move_id.js_add_outstanding_line(statement_line.line_ids[0].id)
        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": -90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 66.66,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_1.account_id.id,
                    "amount_currency": 23.34,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 23.34,
                    "reconciled": True,
                },
            ],
        )

        statement_line_2 = self._create_st_line(amount=-90, update_create_date=False)
        move_line_2 = self._create_invoice_line(
            "in_invoice",
            currency_id=self.other_currency.id,
            invoice_payment_term_id=payment_term.id,
            invoice_line_ids=[{"price_unit": 400.0}],
        )
        statement_line_2.set_line_bank_statement_line(move_line_2.ids)
        self.assertRecordValues(
            statement_line_2.line_ids,
            [
                {
                    "account_id": statement_line_2.journal_id.default_account_id.id,
                    "amount_currency": -90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": 133.32,
                    "currency_id": self.other_currency.id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": 133.32,
                    "currency_id": self.other_currency.id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": 133.36,
                    "currency_id": self.other_currency.id,
                    "balance": 66.68,
                    "reconciled": True,
                },
                {
                    "account_id": suspense_account.id,
                    "amount_currency": -110.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -110.0,
                    "reconciled": False,
                },
            ],
        )
        statement_line_2 = self._create_st_line(amount=-90, update_create_date=False)
        move_line_2 = self._create_invoice_line(
            "in_invoice",
            currency_id=self.other_currency.id,
            invoice_payment_term_id=payment_term.id,
            invoice_line_ids=[{"price_unit": 400.0}],
        )
        move_line_2.move_id.js_add_outstanding_line(statement_line_2.line_ids[0].id)
        self.assertRecordValues(
            statement_line_2.line_ids,
            [
                {
                    "account_id": statement_line_2.journal_id.default_account_id.id,
                    "amount_currency": -90.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": 133.32,
                    "currency_id": self.other_currency.id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_2.account_id.id,
                    "amount_currency": 46.68,
                    "currency_id": self.other_currency.id,
                    "balance": 23.34,
                    "reconciled": True,
                },
            ],
        )

        new_journal = self.env["account.journal"].create(
            {
                "name": "test",
                "code": "TBNK",
                "type": "bank",
                "currency_id": self.other_currency.id,
            }
        )
        suspense_account_other = new_journal.suspense_account_id
        statement_line_3 = self._create_st_line(
            amount=-180, journal_id=new_journal.id, update_create_date=False
        )
        move_line_3 = self._create_invoice_line(
            "in_invoice",
            invoice_payment_term_id=payment_term.id,
            invoice_line_ids=[{"price_unit": 200.0}],
        )
        statement_line_3.set_line_bank_statement_line(move_line_3.ids)
        self.assertRecordValues(
            statement_line_3.line_ids,
            [
                {
                    "account_id": statement_line_3.journal_id.default_account_id.id,
                    "amount_currency": -180.0,
                    "currency_id": self.other_currency.id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": 66.66,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": 66.66,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": 66.68,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 66.68,
                    "reconciled": True,
                },
                {
                    "account_id": suspense_account_other.id,
                    "amount_currency": -220.0,
                    "currency_id": self.other_currency.id,
                    "balance": -110.0,
                    "reconciled": False,
                },
            ],
        )
        statement_line_3 = self._create_st_line(
            amount=-180, journal_id=new_journal.id, update_create_date=False
        )
        move_line_3 = self._create_invoice_line(
            "in_invoice",
            invoice_payment_term_id=payment_term.id,
            invoice_line_ids=[{"price_unit": 200.0}],
        )
        move_line_3.move_id.js_add_outstanding_line(statement_line_3.line_ids[0].id)
        self.assertRecordValues(
            statement_line_3.line_ids,
            [
                {
                    "account_id": statement_line_3.journal_id.default_account_id.id,
                    "amount_currency": -180.0,
                    "currency_id": self.other_currency.id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": 66.66,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_3.account_id.id,
                    "amount_currency": 23.34,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 23.34,
                    "reconciled": True,
                },
            ],
        )

        statement_line_4 = self._create_st_line(
            amount=-180, journal_id=new_journal.id, update_create_date=False
        )
        move_line_4 = self._create_invoice_line(
            "in_invoice",
            currency_id=self.other_currency.id,
            invoice_payment_term_id=payment_term.id,
            invoice_line_ids=[{"price_unit": 400.0}],
        )
        statement_line_4.set_line_bank_statement_line(move_line_4.ids)
        self.assertRecordValues(
            statement_line_4.line_ids,
            [
                {
                    "account_id": statement_line_4.journal_id.default_account_id.id,
                    "amount_currency": -180.0,
                    "currency_id": self.other_currency.id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_4.account_id.id,
                    "amount_currency": 133.32,
                    "currency_id": self.other_currency.id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_4.account_id.id,
                    "amount_currency": 133.32,
                    "currency_id": self.other_currency.id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_4.account_id.id,
                    "amount_currency": 133.36,
                    "currency_id": self.other_currency.id,
                    "balance": 66.68,
                    "reconciled": True,
                },
                {
                    "account_id": suspense_account_other.id,
                    "amount_currency": -220.0,
                    "currency_id": self.other_currency.id,
                    "balance": -110.0,
                    "reconciled": False,
                },
            ],
        )
        statement_line_4 = self._create_st_line(
            amount=-180, journal_id=new_journal.id, update_create_date=False
        )
        move_line_4 = self._create_invoice_line(
            "in_invoice",
            currency_id=self.other_currency.id,
            invoice_payment_term_id=payment_term.id,
            invoice_line_ids=[{"price_unit": 400.0}],
        )
        move_line_4.move_id.js_add_outstanding_line(statement_line_4.line_ids[0].id)
        self.assertRecordValues(
            statement_line_4.line_ids,
            [
                {
                    "account_id": statement_line_4.journal_id.default_account_id.id,
                    "amount_currency": -180.0,
                    "currency_id": self.other_currency.id,
                    "balance": -90.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line_4.account_id.id,
                    "amount_currency": 133.32,
                    "currency_id": self.other_currency.id,
                    "balance": 66.66,
                    "reconciled": True,
                },
                {
                    "account_id": move_line_4.account_id.id,
                    "amount_currency": 46.68,
                    "currency_id": self.other_currency.id,
                    "balance": 23.34,
                    "reconciled": True,
                },
            ],
        )

        for move in (move_line_1 + move_line_2 + move_line_3 + move_line_4).mapped(
            "move_id"
        ):
            self.assertEqual(move.payment_state, "partial")

    def test_create_rule_during_reconcile_with_previous_statements(self):
        refs = (
            "TEST REFERENCE TO NORMALIZE   123,12",
            "TEST REFERENCE TO NORMALIZE  234,23",
            "TEST REFERENCE TO NORMALIZE 345,12",
            "TEST REFERENCE TO NORMALIZE   234,12",
            "TEST REFERENCE TO NORMALIZE 123,12",
        )
        bank_lines = self.env["account.bank.statement.line"].create(
            [
                {
                    "journal_id": self.company_data["default_journal_bank"].id,
                    "date": "2020-01-01",
                    "payment_ref": payment_ref,
                    "amount": 100,
                    "sequence": 1,
                    "counterpart_account_id": self.account_revenue_1.id,
                }
                for payment_ref in refs
            ]
        )

        bank_lines[-1].set_account_bank_statement_line(
            bank_lines[-1].line_ids[-1].id, self.account_revenue_1.id
        )

        rule = self.env["account.reconcile.model"].search(
            [
                ("match_label_param", "=", "TEST\\ REFERENCE\\ TO\\ NORMALIZE\\ "),
            ],
            limit=1,
        )
        self.assertTrue(rule)

    def test_auto_match_multiple_candidates_select_closer_prior_date(self):
        self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-08",
            invoice_line_ids=[{"price_unit": 150}],
        )
        self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-06",
            invoice_line_ids=[{"price_unit": 150}],
        )
        statement_line = self._create_st_line(
            amount=150,
            partner_id=self.partner_a.id,
            date="2017-01-08",
            update_create_date=False,
        )
        statement_line._try_auto_reconcile_statement_lines()
        self.assertFalse(statement_line.line_ids[-1].reconciled_lines_ids)

    def test_auto_match_one_canditate_selected_prior_date(self):
        self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-10",
            invoice_line_ids=[{"price_unit": 150}],
        )
        move_line_2 = self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-08",
            invoice_line_ids=[{"price_unit": 150}],
        )
        statement_line = self._create_st_line(
            amount=150,
            partner_id=self.partner_a.id,
            date="2017-01-08",
            update_create_date=False,
        )
        statement_line._try_auto_reconcile_statement_lines()
        self.assertEqual(statement_line.line_ids[-1].reconciled_lines_ids, move_line_2)

    def test_auto_match_no_canditate_selected_prior_date(self):
        self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-10",
            invoice_line_ids=[{"price_unit": 150}],
        )
        self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-09",
            invoice_line_ids=[{"price_unit": 150}],
        )
        statement_line = self._create_st_line(
            amount=150,
            partner_id=self.partner_a.id,
            date="2017-01-08",
            update_create_date=False,
        )
        statement_line._try_auto_reconcile_statement_lines()
        self.assertFalse(statement_line.line_ids[-1].reconciled_lines_ids)

    def test_set_partner_on_statement_line_reconciles_with_move_line_missing_invoice_date(
        self,
    ):
        draft_move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create({"name": "line", "price_unit": 100})
                ],
            }
        )
        self.assertFalse(draft_move.line_ids[0].invoice_date)

        prior_move_line = self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-08",
            invoice_line_ids=[{"price_unit": 100}],
        )
        statement_line = self._create_st_line(100.0, date="2017-01-10")
        statement_line.set_partner_bank_statement_line(self.partner_a.id)

        self.assertEqual(statement_line.partner_id, self.partner_a)
        self.assertEqual(
            statement_line.line_ids[-1].reconciled_lines_ids, prior_move_line
        )

    def test_edit_statement_line_with_exchange_diff(self):
        chf_currency = self.setup_other_currency(
            "CHF", rates=[("2016-01-01", 2.0), ("2016-06-20", 1.0)]
        )
        chf_journal = self.env["account.journal"].create(
            {
                "name": "Test Bank CHF",
                "type": "bank",
                "code": "TBCHF",
                "currency_id": chf_currency.id,
            }
        )
        invoice_line = self._create_invoice_line(
            "out_invoice",
            invoice_date="2016-06-15",
            invoice_line_ids=[{"price_unit": 1000.0}],
            currency_id=chf_currency.id,
        )
        st_line = self._create_st_line(
            950.0,
            date="2016-06-21",
            update_create_date=False,
            foreign_currency_id=chf_currency.id,
            journal_id=chf_journal.id,
        )
        st_line.set_line_bank_statement_line(invoice_line.ids)
        st_line.edit_reconcile_line(
            st_line.line_ids[1].id, {"balance": -1000, "amount_currency": -1000}
        )
        self.assertEqual(invoice_line.move_id.display_state, "paid")
        self.assertRecordValues(
            st_line.line_ids,
            [
                {"balance": 950.0, "reconciled": False},
                {"balance": -1000.0, "reconciled": True},
                {"balance": 50.0, "reconciled": False},
            ],
        )

    def test_reconcile_epd_with_exchange_diff(self):
        chf_currency = self.setup_other_currency(
            "CHF", rates=[("2016-01-01", 2.0), ("2016-06-20", 4.0)]
        )
        invoice_line = self._create_invoice_line(
            "out_invoice",
            invoice_date="2016-06-15",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 100.0}],
            currency_id=chf_currency.id,
        )
        st_line = self._create_st_line(
            22.5,
            date="2016-06-21",
            update_create_date=False,
            foreign_currency_id=chf_currency.id,
        )
        st_line.set_line_bank_statement_line(invoice_line.ids)
        payment_move = invoice_line.move_id.matched_payment_ids.move_id
        self.assertTrue(payment_move)
        outstanding_line = payment_move.line_ids.filtered(
            lambda line: line.account_type == "asset_current"
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "partner_id": self.partner_a.id,
                    "balance": 22.5,
                    "amount_currency": 22.5,
                    "reconciled": False,
                },
                {
                    "account_id": outstanding_line.account_id.id,
                    "partner_id": self.partner_a.id,
                    "balance": -22.5,
                    "amount_currency": -90.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_epd_with_partial(self):
        st_line = self._create_st_line(
            70.0, date="2017-01-10", update_create_date=False
        )
        inv_line_with_epd = self._create_invoice_line(
            "out_invoice",
            date="2017-01-04",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        st_line.set_line_bank_statement_line(inv_line_with_epd.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "balance": 70.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line_with_epd.account_id.id,
                    "balance": -70.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_bill_epd_with_larger_statement_line(self):
        st_line = self._create_st_line(
            -200.0, date="2017-01-10", update_create_date=False
        )
        early_pay_acc = self.env.company.account_config_id.account_journal_early_pay_discount_gain_account_id
        bill_line_with_epd = self._create_invoice_line(
            "in_invoice",
            date="2017-01-04",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        st_line.set_line_bank_statement_line(bill_line_with_epd.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "balance": -200.0,
                    "reconciled": False,
                },
                {
                    "account_id": bill_line_with_epd.account_id.id,
                    "balance": 100.0,
                    "reconciled": True,
                },
                {"account_id": early_pay_acc.id, "balance": -10.0, "reconciled": False},
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "balance": 110.0,
                    "reconciled": False,
                },
            ],
        )

    def test_line_computation_on_edit_line(self):
        usd_currency = self.setup_other_currency("USD", rates=[("2017-01-01", 2.00)])
        eur_currency = self.setup_other_currency("EUR", rates=[("2017-01-01", 1.00)])
        eur_journal = self.env["account.journal"].create(
            {
                "name": "Test Bank EUR",
                "type": "bank",
                "code": "TBEUR",
                "currency_id": eur_currency.id,
            }
        )
        st_line = self._create_st_line(
            5000, date="2017-01-10", update_create_date=False, journal_id=eur_journal.id
        )
        eur_invoice_line = self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-10",
            invoice_line_ids=[{"price_unit": 1000.0}],
            currency_id=eur_currency.id,
        )
        usd_invoice_line = self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-10",
            invoice_line_ids=[{"price_unit": 1000.0}],
            currency_id=usd_currency.id,
        )
        st_line.set_line_bank_statement_line(usd_invoice_line.id)
        st_line.set_line_bank_statement_line(eur_invoice_line.id)
        st_line.set_account_bank_statement_line(
            st_line.line_ids[-1].id, self.account_revenue_1.id
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id, {"balance": -2000, "amount_currency": -1000}
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {"amount_currency": 5000.0, "balance": 10000.0, "reconciled": False},
                {"amount_currency": -1000.0, "balance": -1000.0, "reconciled": True},
                {"amount_currency": -1000.0, "balance": -2000.0, "reconciled": True},
                {"amount_currency": -1000.0, "balance": -2000.0, "reconciled": False},
                {"amount_currency": -2500.0, "balance": -5000.0, "reconciled": False},
            ],
        )

    def test_reconcile_partialed_amounts(self):
        st_line_50 = self._create_st_line(50.0, update_create_date=False)
        st_line_300 = self._create_st_line(300.0, update_create_date=False)
        st_line_400 = self._create_st_line(400.0, update_create_date=False)
        st_line_500 = self._create_st_line(500.0, update_create_date=False)
        inv_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 1000.0}]
        )

        st_line_50.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line_50.line_ids,
            [
                {
                    "account_id": st_line_50.journal_id.default_account_id.id,
                    "balance": 50.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "balance": -50.0,
                    "reconciled": True,
                },
            ],
        )

        st_line_300.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line_300.line_ids,
            [
                {
                    "account_id": st_line_300.journal_id.default_account_id.id,
                    "balance": 300.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "balance": -300.0,
                    "reconciled": True,
                },
            ],
        )

        st_line_400.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line_400.line_ids,
            [
                {
                    "account_id": st_line_400.journal_id.default_account_id.id,
                    "balance": 400.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "balance": -400.0,
                    "reconciled": True,
                },
            ],
        )

        st_line_500.set_line_bank_statement_line(inv_line.id)
        self.assertRecordValues(
            st_line_500.line_ids,
            [
                {
                    "account_id": st_line_500.journal_id.default_account_id.id,
                    "balance": 500.0,
                    "reconciled": False,
                },
                {
                    "account_id": inv_line.account_id.id,
                    "balance": -250.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line_500.journal_id.suspense_account_id.id,
                    "balance": -250.0,
                    "reconciled": False,
                },
            ],
        )

    def test_full_amount_switch_html_multi_statements(self):
        st_line_50 = self._create_st_line(50.0, update_create_date=False)
        st_line_300 = self._create_st_line(300.0, update_create_date=False)
        inv_line = self._create_invoice_line(
            "out_invoice", invoice_line_ids=[{"price_unit": 350.0}]
        )

        st_line_50.set_line_bank_statement_line(inv_line.id)
        st_line_300.set_line_bank_statement_line(inv_line.id)

        self.assertFalse(inv_line.full_amount_switch_html)
        self.assertTrue(
            any(line.full_amount_switch_html for line in st_line_50.line_ids)
        )
        self.assertTrue(
            any(line.full_amount_switch_html for line in st_line_300.line_ids)
        )

    def test_apply_full_amount_html_currencies(self):
        st_line = self._create_st_line(50.0, update_create_date=False)
        invoice_line = self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-01",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 150.0}],
            currency_id=self.other_currency.id,
        )
        st_line.set_line_bank_statement_line(invoice_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "balance": 50.0,
                    "amount_currency": 50.0,
                    "reconciled": False,
                },
                {
                    "account_id": invoice_line.account_id.id,
                    "balance": -50.0,
                    "amount_currency": -100.0,
                    "reconciled": True,
                },
            ],
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id, {"balance": -150, "amount_currency": -300}
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "balance": 50.0,
                    "amount_currency": 50.0,
                    "reconciled": False,
                },
                {
                    "account_id": invoice_line.account_id.id,
                    "balance": -150.0,
                    "amount_currency": -300.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "balance": 100.0,
                    "amount_currency": 100.0,
                    "reconciled": False,
                },
            ],
        )

    def test_edit_reconcile_line_with_positive_balance(self):
        st_line = self._create_st_line(50.0, update_create_date=False)
        invoice_line = self._create_invoice_line(
            "out_invoice",
            invoice_date="2017-01-01",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 150.0}],
            currency_id=self.other_currency.id,
        )
        st_line.set_line_bank_statement_line(invoice_line.id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "balance": 50.0,
                    "amount_currency": 50.0,
                    "reconciled": False,
                },
                {
                    "account_id": invoice_line.account_id.id,
                    "balance": -50.0,
                    "amount_currency": -100.0,
                    "reconciled": True,
                },
            ],
        )
        st_line.edit_reconcile_line(
            st_line.line_ids[-1].id, {"balance": 150, "amount_currency": 300}
        )
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "balance": 50.0,
                    "amount_currency": 50.0,
                    "reconciled": False,
                },
                {
                    "account_id": invoice_line.account_id.id,
                    "balance": 150.0,
                    "amount_currency": 300.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "balance": -200.0,
                    "amount_currency": -200.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reco_model_empty_space_at_the_end(self):
        st_line_1 = self._create_st_line(
            amount=100,
            payment_ref="Pret                            ",
            update_create_date=False,
        )
        st_line_2 = self._create_st_line(
            amount=100,
            payment_ref="Course                            ",
            update_create_date=False,
        )

        st_line_1.set_account_bank_statement_line(
            st_line_1.line_ids[-1].id, self.account_revenue_1.id
        )
        st_line_2.set_account_bank_statement_line(
            st_line_2.line_ids[-1].id, self.account_revenue_1.id
        )

        reco_model = self.env["account.reconcile.model"].search(
            [
                ("match_label", "=", "match_regex"),
                (
                    "match_label_param",
                    "=",
                    "\\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ ",
                ),
            ]
        )
        self.assertFalse(reco_model.exists())

    def test_set_partner_multiple_statement_line(self):
        invoice_1 = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_line_ids=[{"price_unit": 1000.0}],
        )
        invoice_2 = self._create_invoice_line(
            "out_invoice",
            partner_id=self.partner_a.id,
            invoice_line_ids=[{"price_unit": 1500.0}],
        )
        statement_line_1 = self._create_st_line(
            amount=100, update_create_date=False, partner_id=False
        )
        statement_line_2 = self._create_st_line(
            1000.0,
            partner_name="xyz",
            payment_ref=invoice_1.move_id.name,
            update_create_date=False,
        )
        statement_line_3 = self._create_st_line(
            1500.0,
            partner_name="xyz",
            payment_ref=invoice_2.move_id.name,
            update_create_date=False,
        )
        self.env.cr.flush()

        (statement_line_1 + statement_line_2).with_context(
            tracking_disable=False,
            mail_notrack=False,
        ).set_partner_bank_statement_line(self.partner_a.id)
        self.env.cr.flush()

        self.assertEqual(statement_line_1.partner_id, self.partner_a)
        self.assertEqual(statement_line_2.partner_id, self.partner_a)
        self.assertEqual(statement_line_3.partner_id, self.partner_a)

    def test_set_account_multiple_statement_lines(self):
        st_line_1 = self._create_st_line(500.0, update_create_date=False)
        st_line_2 = self._create_st_line(500.0, update_create_date=False)

        (st_line_1 + st_line_2).set_account_bank_statement_line(
            [st_line_1.line_ids[-1].id, st_line_2.line_ids[-1].id],
            self.account_revenue_1.id,
        )
        self.assertRecordValues(
            st_line_1.line_ids,
            [
                {
                    "account_id": st_line_1.journal_id.default_account_id.id,
                    "amount_currency": 500.0,
                    "balance": 500.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.company_data["default_account_revenue"].id,
                    "amount_currency": -500.0,
                    "balance": -500.0,
                    "reconciled": False,
                },
            ],
        )
        self.assertRecordValues(
            st_line_2.line_ids,
            [
                {
                    "account_id": st_line_2.journal_id.default_account_id.id,
                    "amount_currency": 500.0,
                    "balance": 500.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.company_data["default_account_revenue"].id,
                    "amount_currency": -500.0,
                    "balance": -500.0,
                    "reconciled": False,
                },
            ],
        )

    def test_remove_epd_with_tax(self):
        tax = self.env["account.tax"].create(
            {
                "name": "new_tax",
                "amount_type": "percent",
                "amount": 20.0,
                "type_tax_use": "sale",
            }
        )
        suspense_account = self.company_data["default_journal_bank"].suspense_account_id
        early_pay_acc = self.env.company.account_config_id.account_journal_early_pay_discount_loss_account_id

        statement_line = self._create_st_line(
            amount=200, date="2017-01-10", update_create_date=False
        )
        move_line = self._create_invoice_line(
            "out_invoice",
            date="2017-01-04",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 100.0, "tax_ids": tax.ids}],
        )
        statement_line.set_line_bank_statement_line(move_line.ids)

        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": 200.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line.account_id.id,
                    "amount_currency": -120.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -120.0,
                    "reconciled": True,
                },
                {
                    "account_id": early_pay_acc.id,
                    "amount_currency": 10.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 10.0,
                    "reconciled": False,
                },
                {
                    "account_id": self.account_revenue_1.id,
                    "amount_currency": 2.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 2.0,
                    "reconciled": False,
                },
                {
                    "account_id": suspense_account.id,
                    "amount_currency": -92.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -92.0,
                    "reconciled": False,
                },
            ],
        )

        epd_line = statement_line.line_ids.filtered(
            lambda line: line.account_id == early_pay_acc
        )
        statement_line.remove_reconciled_line(epd_line.ids)

        self.assertRecordValues(
            statement_line.line_ids,
            [
                {
                    "account_id": statement_line.journal_id.default_account_id.id,
                    "amount_currency": 200.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": 200.0,
                    "reconciled": False,
                },
                {
                    "account_id": move_line.account_id.id,
                    "amount_currency": -120.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -120.0,
                    "reconciled": True,
                },
                {
                    "account_id": suspense_account.id,
                    "amount_currency": -80.0,
                    "currency_id": self.company_data["currency"].id,
                    "balance": -80.0,
                    "reconciled": False,
                },
            ],
        )

    def test_remove_reconciled_line_with_tax_reconcile_account(self):
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[
                {"price_unit": 100.0, "tax_ids": [Command.set(self.default_tax.ids)]}
            ],
        )
        tax_line = inv_line.move_id.line_ids.filtered(lambda l: l.tax_line_id)
        st_line = self._create_st_line(-200.0, update_create_date=False)
        st_line.set_line_bank_statement_line([tax_line.id])
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": -200.0,
                    "reconciled": False,
                },
                {
                    "account_id": tax_line.account_id.id,
                    "tax_ids": [],
                    "tax_line_id": tax_line.tax_line_id.id,
                    "balance": 10.0,
                    "reconciled": True,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 190.0,
                    "reconciled": False,
                },
            ],
        )
        st_line.remove_reconciled_line(st_line.line_ids[-2].id)
        self.assertRecordValues(
            st_line.line_ids,
            [
                {
                    "account_id": st_line.journal_id.default_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": -200.0,
                    "reconciled": False,
                },
                {
                    "account_id": st_line.journal_id.suspense_account_id.id,
                    "tax_ids": [],
                    "tax_line_id": False,
                    "balance": 200.0,
                    "reconciled": False,
                },
            ],
        )

    def test_early_payment_discount_multi_bill_statement(self):
        self.company_data[
            "default_journal_bank"
        ].outbound_payment_channel_ids.payment_account_id = False
        inv_line_with_epd = self._create_invoice_line(
            "in_invoice",
            date="2017-01-10",
            invoice_payment_term_id=self.early_payment_term.id,
            invoice_line_ids=[{"price_unit": 100.0}],
        )
        payment = (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move", active_ids=inv_line_with_epd.move_id.ids
            )
            .create(
                {
                    "payment_date": "2017-01-10",
                }
            )
            ._create_payments()
        )

        st_line = self._create_st_line(
            -100.0, date="2017-01-11", update_create_date=False
        )
        st_line.set_line_bank_statement_line([inv_line_with_epd.id])
        self.assertEqual(inv_line_with_epd.move_id.payment_state, "paid")
        self.assertTrue(
            payment.move_id,
            "'paid' below is only correct while the payment carries a journal entry",
        )
        self.assertEqual(payment.state, "paid")

    def test_credit_warning_excludes_unreconciled_bank_statement_line(self):
        self.env.company.account_config_id.account_use_credit_limit = True
        self.partner_a.credit_limit = 1000.0
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 2000.0, "tax_ids": []}],
        )
        invoice = inv_line.move_id
        invoice.action_draft()
        self.assertTrue(invoice.partner_credit_warning)

        self._create_st_line(
            amount=1500.0,
            date="2017-01-01",
            partner_id=self.partner_a.id,
        )
        invoice.invalidate_recordset(["partner_credit_warning"])
        self.assertFalse(invoice.partner_credit_warning)

    def test_credit_warning_excludes_reconciled_bank_statement_line(self):
        self.env.company.account_config_id.account_use_credit_limit = True
        self.partner_a.credit_limit = 1000.0
        inv_line = self._create_invoice_line(
            "out_invoice",
            invoice_line_ids=[{"price_unit": 2000.0, "tax_ids": []}],
        )
        invoice = inv_line.move_id
        invoice.action_draft()
        self.assertTrue(invoice.partner_credit_warning)

        st_line = self._create_st_line(
            amount=1500.0,
            date="2017-01-01",
            partner_id=self.partner_a.id,
        )
        invoice.action_post()
        bank_cash_line = st_line.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == "asset_cash"
        )
        invoice.js_add_outstanding_line(bank_cash_line.id)
        invoice.action_draft()
        self.assertFalse(invoice.partner_credit_warning)

    def test_common_substring(self):
        payment_ref1 = "RF33 4434 5675 9111 4543 8787"
        payment_ref2 = "RF13 4434 5675 9111 4512 7777"
        payment_ref3 = "RF67 3791 6912 4434 5675 9132"
        non_matching_ref = "ABCDEFG"
        BankStatementLine = self.env["account.bank.statement.line"]

        self.assertEqual(
            BankStatementLine._get_common_substring([payment_ref1, payment_ref2]),
            re.escape("3 4434 5675 9111 45"),
        )
        self.assertEqual(
            BankStatementLine._get_common_substring(
                [payment_ref1, payment_ref2, payment_ref3]
            ),
            re.escape(" 4434 5675 91"),
        )
        self.assertIsNone(
            BankStatementLine._get_common_substring([payment_ref1, non_matching_ref])
        )
        self.assertIsNone(
            BankStatementLine._get_common_substring(
                [payment_ref1, payment_ref2, non_matching_ref]
            )
        )
