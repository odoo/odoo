import logging

import odoo
from odoo import fields

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

_logger = logging.getLogger(__name__)


@odoo.tests.tagged("post_install", "-at_install")
class TestPosAccountingUnits(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product = self.create_product("AcctProd", self.categ_basic, 100, 50)

    def test_create_payment_moves_idempotent_on_reinvoke(self):
        self._start_pos_session(self.cash_pm1 | self.bank_pm1, 0)
        orders = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product, 1)],
                    "payments": [(self.bank_pm1, 100)],
                    "customer": self.customer,
                    "uuid": "acct-idem-1",
                },
            ]
        )
        order = orders["acct-idem-1"]

        order.action_pos_order_invoice()
        self.assertTrue(order.account_move, "order should be invoiced")

        payments = order._get_payments()
        booked = payments.filtered(lambda p: p.account_move_id)
        self.assertTrue(booked, "the bank payment should have booked a move")
        moves_before = booked.account_move_id
        _logger.info("idempotency: %s move(s) before re-invoke", len(moves_before))

        result = payments._create_payment_moves()
        self.assertFalse(
            result,
            "re-invoking _create_payment_moves double-booked the payment",
        )
        self.assertEqual(booked.account_move_id, moves_before)

    def test_create_payment_moves_skips_pay_later_and_zero(self):
        self._start_pos_session(self.cash_pm1 | self.pay_later_pm, 0)
        orders = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product, 1)],
                    "payments": [(self.pay_later_pm, 100)],
                    "customer": self.customer,
                    "uuid": "acct-paylater-1",
                },
            ]
        )
        order = orders["acct-paylater-1"]
        result = order._get_payments()._create_payment_moves()
        self.assertFalse(
            result, "pay_later payment must not book an invoice payment move"
        )

    def test_prepare_aml_values_per_nature_combine_payment(self):
        self._start_pos_session(self.cash_pm1 | self.bank_pm1, 0)
        taxed = self.create_product(
            "AcctTaxed", self.categ_basic, 100, 50, tax_ids=self.taxes["tax7"].ids
        )
        orders = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(taxed, 1)],
                    "payments": [(self.bank_pm1, 107)],
                    "customer": self.customer,
                    "uuid": "acct-aml-combine",
                },
            ]
        )
        order = orders["acct-aml-combine"]
        aml = order._prepare_aml_values_list_per_nature()
        _logger.info("aml natures: %s", {k: len(v) for k, v in aml.items()})

        self.assertTrue(aml["product"], "a sales/product line must be emitted")
        self.assertTrue(aml["tax"], "a tax line must be emitted for a taxed order")
        self.assertTrue(aml["payment_terms"], "a receivable line must be emitted")

        pt_total = sum(line["amount_currency"] for line in aml["payment_terms"])
        self.assertAlmostEqual(pt_total, order.amount_paid, places=2)

        self.assertTrue(all(not line["partner_id"] for line in aml["payment_terms"]))

    def test_prepare_aml_values_per_nature_split_payment_has_partner(self):
        self._start_pos_session(self.cash_pm1 | self.bank_split_pm1, 0)
        orders = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product, 1)],
                    "payments": [(self.bank_split_pm1, 100)],
                    "customer": self.customer,
                    "uuid": "acct-aml-split",
                },
            ]
        )
        order = orders["acct-aml-split"]
        aml = order._prepare_aml_values_list_per_nature()
        self.assertTrue(aml["payment_terms"])
        self.assertTrue(
            all(
                line["partner_id"] == self.customer.commercial_partner_id.id
                for line in aml["payment_terms"]
            ),
            "split payment receivable line must carry the customer partner",
        )

    def test_prepare_aml_values_per_nature_cash_rounding_add_invoice_line(self):
        cash_rounding = self.env["account.cash.rounding"].create(
            {
                "name": "acct-cr-add-line",
                "rounding": 0.05,
                "rounding_method": "HALF-UP",
                "strategy": "add_invoice_line",
                "profit_account_id": self.env.company.account_config_id.default_cash_difference_income_account_id.id,
                "loss_account_id": self.env.company.account_config_id.default_cash_difference_expense_account_id.id,
            }
        )
        self.config.write(
            {
                "cash_rounding": True,
                "rounding_method": cash_rounding.id,
                "only_round_cash_method": False,
            }
        )
        rounded_product = self.create_product("AcctRound", self.categ_basic, 9.99, 5)
        self._start_pos_session(self.cash_pm1, 0)
        orders = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(rounded_product, 1)],
                    "payments": [(self.cash_pm1, 10.0)],
                    "customer": self.customer,
                    "uuid": "acct-aml-round",
                },
            ]
        )
        order = orders["acct-aml-round"]
        aml = order._prepare_aml_values_list_per_nature()
        _logger.info("cash_rounding natures: %s", {k: len(v) for k, v in aml.items()})
        self.assertTrue(
            aml["cash_rounding"], "a cash_rounding line must be emitted for a 0.05 diff"
        )
        rounding_accounts = {
            cash_rounding.profit_account_id.id,
            cash_rounding.loss_account_id.id,
        }
        self.assertTrue(
            all(
                line["account_id"] in rounding_accounts for line in aml["cash_rounding"]
            ),
            "cash_rounding line must post to the rounding profit/loss account",
        )

    def test_get_balancing_account_uses_company_pos_receivable(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        expected = (
            self.env.company.account_config_id.account_default_pos_receivable_account_id
        )
        self.assertTrue(
            expected, "the company should carry a default POS receivable account"
        )
        self.assertEqual(session._get_balancing_account(), expected)

    def test_prepare_balancing_line_vals_same_currency(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        balancing_account = session._get_balancing_account()
        move = self.env["account.move"].create(
            {"journal_id": session.config_id.journal_id.id, "ref": "test-balancing"}
        )

        vals = session._prepare_balancing_line_vals(50.0, move, balancing_account)
        self.assertEqual(vals["account_id"], balancing_account.id)
        self.assertEqual(vals["move_id"], move.id)
        self.assertFalse(vals["partner_id"])
        self.assertAlmostEqual(vals["credit"], 50.0)
        self.assertAlmostEqual(vals["debit"], 0.0)
        self.assertNotIn("amount_currency", vals)

        vals_neg = session._prepare_balancing_line_vals(-30.0, move, balancing_account)
        self.assertAlmostEqual(vals_neg["debit"], 30.0)
        self.assertAlmostEqual(vals_neg["credit"], 0.0)


@odoo.tests.tagged("post_install", "-at_install")
class TestPosSessionAmountBuilders(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_update_amounts_accumulates_and_copies(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        self.assertTrue(
            session.is_in_company_currency,
            "basic_config is expected to run in company currency",
        )
        date = fields.Datetime.now()
        old = {"amount": 10.0, "amount_converted": 10.0}
        new = session._update_amounts(old, {"amount": 5.0}, date)
        self.assertEqual(new["amount"], 15.0)
        self.assertEqual(new["amount_converted"], 15.0)
        self.assertEqual(old, {"amount": 10.0, "amount_converted": 10.0})

    def test_update_amounts_accumulates_the_base_unconverted(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        date = fields.Datetime.now()
        old = {"amount": 0.0, "amount_converted": 0.0, "base_amount_converted": 0.0}
        new = session._update_amounts(
            old, {"amount": 7.0, "base_amount_converted": 100.0}, date
        )
        self.assertEqual(new["amount"], 7.0)
        self.assertEqual(new["base_amount_converted"], 100.0)
        self.assertNotIn("base_amount", new)

    def test_credit_and_debit_amounts_sign_split(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        partial = {
            "account_id": self.env.company.account_config_id.account_default_pos_receivable_account_id.id
        }

        credit = session._prepare_credit_line_vals(dict(partial), 50.0, 50.0)
        self.assertAlmostEqual(credit["credit"], 50.0)
        self.assertAlmostEqual(credit["debit"], 0.0)

        credit_neg = session._prepare_credit_line_vals(dict(partial), -30.0, -30.0)
        self.assertAlmostEqual(credit_neg["debit"], 30.0)
        self.assertAlmostEqual(credit_neg["credit"], 0.0)

        debit = session._prepare_debit_line_vals(dict(partial), 40.0, 40.0)
        self.assertAlmostEqual(debit["debit"], 40.0)
        self.assertAlmostEqual(debit["credit"], 0.0)

    def test_increase_customer_ranks_batches_per_partner(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        product = self.create_product("RankProd", self.categ_basic, 50, 20)
        orders = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(product, 1)],
                    "payments": [(self.cash_pm1, 50)],
                    "customer": self.customer,
                    "uuid": "rank-1",
                },
                {
                    "pos_order_lines_ui_args": [(product, 1)],
                    "payments": [(self.cash_pm1, 50)],
                    "customer": self.customer,
                    "uuid": "rank-2",
                },
            ]
        )
        recs = orders["rank-1"] | orders["rank-2"]
        self.customer.invalidate_recordset(["customer_rank"])
        before = self.customer.customer_rank
        session._increase_customer_ranks(recs)
        self.customer.invalidate_recordset(["customer_rank"])
        self.assertEqual(
            self.customer.customer_rank,
            before + 2,
            "two non-invoiced orders for the same partner must bump rank by 2",
        )
