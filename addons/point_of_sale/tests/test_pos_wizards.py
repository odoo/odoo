from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged("post_install", "-at_install")
class TestPosWizards(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.product = cls.create_product("Wizard product", cls.categ_basic, 100, 50)

    def setUp(self):
        super().setUp()
        self._start_pos_session(self.cash_pm1 | self.bank_pm1, 0)

    def _create_order(self, **values):
        return self.env["pos.order"].create(
            {
                "session_id": self.pos_session.id,
                "company_id": self.env.company.id,
                "partner_id": self.customer.id,
                "amount_tax": 0,
                "amount_total": 100,
                "amount_paid": 0,
                "amount_return": 0,
                "lines": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "qty": 1,
                            "price_unit": 100,
                            "price_subtotal": 100,
                            "price_subtotal_incl": 100,
                        }
                    )
                ],
                **values,
            }
        )

    def _create_payment(self, order, **values):
        return (
            self.env["pos.make.payment"]
            .with_context(
                active_model="pos.order",
                active_id=order.id,
                active_ids=order.ids,
            )
            .create(values)
        )

    def _invoice_orders(self, orders, consolidated=True):
        return (
            self.env["pos.make.invoice"]
            .with_context(
                active_ids=orders.ids,
                generate_pdf=False,
            )
            .create({"consolidated_billing": consolidated})
            .action_create_invoices()
        )

    def _create_invoiced_order_refunds(self, orders):
        refunds = self.env["pos.order"]
        for order in orders:
            self._create_payment(order).action_make_payment()
            self._invoice_orders(order)
            refund = self.env["pos.order"].browse(order.action_refund()["res_id"])
            self._create_payment(refund).action_make_payment()
            refunds |= refund
        return refunds

    def test_payment_date_and_reference_are_preserved(self):
        order = self._create_order()
        payment_date = datetime(2026, 8, 1, 12)
        wizard = self._create_payment(
            order,
            amount=40,
            payment_date=payment_date,
            payment_name="Deposit",
        )

        action = wizard.action_make_payment()

        self.assertRecordValues(
            order.payment_ids,
            [
                {
                    "amount": 40,
                    "payment_date": payment_date,
                    "name": "Deposit",
                }
            ],
        )
        self.assertEqual(order.state, "draft")
        self.assertEqual(action["res_model"], "pos.make.payment")
        self.assertAlmostEqual(self._create_payment(order).amount, 60)

    def test_full_payment_finishes_order(self):
        order = self._create_order()

        action = self._create_payment(order).action_make_payment()

        self.assertEqual(order.state, "paid")
        self.assertAlmostEqual(order.amount_paid, 100)
        self.assertEqual(action["type"], "ir.actions.act_window_close")

    def test_payment_method_must_belong_to_session(self):
        order = self._create_order()
        wizard = self._create_payment(order, payment_method_id=self.bank_split_pm1.id)

        with self.assertRaises(ValidationError):
            wizard.action_make_payment()

        self.assertFalse(order.payment_ids)

    def test_payment_configuration_must_match_order(self):
        order = self._create_order()
        other_config = self.config.copy({"name": "Other wizard POS"})
        wizard = self._create_payment(order, config_id=other_config.id)

        with self.assertRaises(UserError):
            wizard.action_make_payment()

        self.assertFalse(order.payment_ids)

    def test_cancelled_order_cannot_receive_payment(self):
        order = self._create_order(state="cancel")

        with self.assertRaises(UserError):
            self._create_payment(order).action_make_payment()

        self.assertFalse(order.payment_ids)

    def test_payment_without_active_order_is_rejected(self):
        wizard = self.env["pos.make.payment"].create(
            {
                "config_id": self.config.id,
                "payment_method_id": self.cash_pm1.id,
                "amount": 10,
            }
        )

        with self.assertRaises(UserError):
            wizard.action_make_payment()

    def test_individual_refund_invoices_in_one_batch(self):
        orders = self._create_order() | self._create_order()
        refunds = self._create_invoiced_order_refunds(orders)

        with self.assertRaises(UserError):
            self._invoice_orders(refunds)
        self._invoice_orders(refunds, consolidated=False)

        self.assertEqual(len(refunds.account_move), 2)
        self.assertEqual(refunds.account_move.mapped("move_type"), ["out_refund"] * 2)
        self.assertEqual(refunds.account_move.reversed_entry_id, orders.account_move)
        self.assertTrue(all(move.state == "posted" for move in refunds.account_move))

    def test_consolidated_invoice_combines_matching_orders(self):
        orders = self._create_order() | self._create_order()
        for order in orders:
            self._create_payment(order).action_make_payment()

        self._invoice_orders(orders)

        self.assertEqual(len(orders.account_move), 1)
        self.assertAlmostEqual(orders.account_move.amount_total, 200)
        self.assertAlmostEqual(orders.account_move.amount_residual, 0)

    def test_confirmation_only_updates_orders_without_customer(self):
        named_order = self._create_order(state="paid")
        anonymous_order = self._create_order(state="paid", partner_id=False)
        orders = named_order | anonymous_order
        action = self._invoice_orders(orders)
        wizard = (
            self.env["pos.confirmation.wizard"]
            .with_context(
                action["context"],
                generate_pdf=False,
            )
            .create({})
        )
        writes = []
        original_write = type(orders).write

        def record_write(records, values):
            if "partner_id" in values:
                writes.append(records.ids)
            return original_write(records, values)

        with patch.object(type(orders), "write", record_write):
            next_action = wizard.action_confirm()

        self.assertEqual(writes, [anonymous_order.ids])
        self.assertEqual(orders.partner_id, self.customer)
        self.assertCountEqual(next_action["context"]["active_ids"], orders.ids)
        self.assertFalse(next_action["context"]["generate_pdf"])

    def test_confirmation_rechecks_ambiguous_customers(self):
        orders = self._create_order(state="paid") | self._create_order(
            state="paid",
            partner_id=False,
        )
        action = self._invoice_orders(orders)
        wizard = (
            self.env["pos.confirmation.wizard"]
            .with_context(action["context"])
            .create({})
        )
        other_partner = self.env["res.partner"].create({"name": "Changed customer"})
        orders[1].partner_id = other_partner

        with self.assertRaises(UserError):
            wizard.action_confirm()

        self.assertEqual(orders[1].partner_id, other_partner)

    def test_confirmation_without_customer_is_rejected(self):
        order = self._create_order(state="paid", partner_id=False)
        wizard = (
            self.env["pos.confirmation.wizard"]
            .with_context(orders=order.ids)
            .create({})
        )

        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_report_rejects_reversed_dates(self):
        wizard = self.env["pos.details.wizard"].create(
            {
                "start_date": "2026-08-02 12:00:00",
                "end_date": "2026-08-01 12:00:00",
                "pos_config_ids": [Command.set(self.config.ids)],
            }
        )

        with self.assertRaises(UserError):
            wizard.action_print_report()

    def test_report_empty_configuration_selection_means_all(self):
        wizard = self.env["pos.details.wizard"].create(
            {"pos_config_ids": [Command.clear()]}
        )
        order = self._create_order()
        self._create_payment(order).action_make_payment()
        wizard.start_date = order.date_order - timedelta(hours=1)
        wizard.end_date = order.date_order + timedelta(hours=1)

        action = wizard.with_context(discard_logo_check=True).action_print_report()
        report = self.env["report.point_of_sale.report_saledetails"].get_sale_details(
            **action["data"]
        )

        self.assertEqual(action["data"]["config_ids"], [])
        self.assertEqual(report["nbr_orders"], 1)
        self.assertAlmostEqual(report["currency"]["total_paid"], 100)

    def test_report_onchanges_and_payload(self):
        with Form(self.env["pos.details.wizard"]) as form:
            form.start_date = datetime(2026, 8, 2, 12)
            form.end_date = datetime(2026, 8, 1, 12)
            self.assertEqual(form.start_date, form.end_date)
            form.start_date = datetime(2026, 8, 3, 12)
            self.assertEqual(form.end_date, form.start_date)
        wizard = form.record

        data = wizard.with_context(discard_logo_check=True).action_print_report()[
            "data"
        ]

        self.assertEqual(data["date_start"], wizard.start_date)
        self.assertEqual(data["date_stop"], wizard.end_date)
        self.assertEqual(data["config_ids"], wizard.pos_config_ids.ids)

    def test_daily_report_uses_explicit_session(self):
        wizard = self.env["pos.daily.sales.reports.wizard"].create(
            {
                "pos_session_id": self.pos_session.id,
            }
        )

        data = wizard.with_context(discard_logo_check=True).action_print_report()[
            "data"
        ]

        self.assertEqual(
            data,
            {
                "date_start": False,
                "date_stop": False,
                "config_ids": self.config.ids,
                "session_ids": self.pos_session.ids,
            },
        )

    def test_daily_report_rejects_multiple_wizards(self):
        wizards = self.env["pos.daily.sales.reports.wizard"].create(
            [
                {"pos_session_id": self.pos_session.id},
                {"pos_session_id": self.pos_session.id},
            ]
        )

        with self.assertRaises(ValueError):
            wizards.action_print_report()

    def test_invoice_count_follows_selection_context(self):
        orders = self._create_order() | self._create_order()
        wizard = (
            self.env["pos.make.invoice"].with_context(active_ids=orders.ids).create({})
        )

        self.assertEqual(wizard.order_count, 2)
        self.assertEqual(wizard.with_context(active_ids=orders[:1].ids).order_count, 1)
        self.assertEqual(wizard.with_context(active_ids=None).order_count, 0)
        self.assertEqual(wizard.order_count, 2)

    def test_invoice_rejects_selection_without_invoiceable_orders(self):
        orders = self._create_order() | self._create_order(state="cancel")

        with self.assertRaises(UserError):
            self._invoice_orders(orders)

        self.assertFalse(orders.account_move)

    def test_invoice_grouping_separates_each_accounting_dimension(self):
        other_config = self.config.copy({"name": "Separate invoicing POS"})
        other_config.open_ui()
        other_partner = self.env["res.partner"].create({"name": "Separate customer"})
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Separate fiscal position",
                "company_id": self.env.company.id,
            }
        )
        orders = self._create_order(state="paid")
        for values in (
            {"session_id": other_config.current_session_id.id},
            {"partner_id": other_partner.id},
            {"user_id": self.simple_accountman.id},
            {"fiscal_position_id": fiscal_position.id},
        ):
            orders |= self._create_order(state="paid", **values)

        self._invoice_orders(orders)

        self.assertEqual(len(orders.account_move), 5)
        for order in orders:
            with self.subTest(order=order.id):
                self.assertEqual(order.account_move.pos_order_ids, order)
                self.assertEqual(order.account_move.partner_id, order.partner_id)
                self.assertEqual(order.account_move.invoice_user_id, order.user_id)
                self.assertEqual(
                    order.account_move.fiscal_position_id, order.fiscal_position_id
                )
                self.assertEqual(
                    order.account_move.journal_id, order.config_id.invoice_journal_id
                )

    def test_split_payment_requires_customer(self):
        config = self.config.copy(
            {
                "name": "Split payment POS",
                "payment_method_ids": [Command.set(self.bank_split_pm1.ids)],
            }
        )
        config.open_ui()
        order = self._create_order(
            partner_id=False, session_id=config.current_session_id.id
        )

        with self.assertRaises(UserError):
            self._create_payment(
                order, payment_method_id=self.bank_split_pm1.id
            ).action_make_payment()

        self.assertFalse(order.payment_ids)

    def test_zero_payment_does_not_create_payment_row(self):
        order = self._create_order()

        action = self._create_payment(order, amount=0).action_make_payment()

        self.assertFalse(order.payment_ids)
        self.assertEqual(order.state, "draft")
        self.assertEqual(action["res_model"], "pos.make.payment")

    def test_payment_defaults_prefer_cash_and_fall_back_to_bank(self):
        order = self._create_order()
        self.assertEqual(self._create_payment(order).payment_method_id, self.cash_pm1)

        config = self.config.copy(
            {
                "name": "Bank only POS",
                "payment_method_ids": [Command.set(self.bank_pm1.ids)],
            }
        )
        config.open_ui()
        order = self._create_order(session_id=config.current_session_id.id)

        self.assertEqual(self._create_payment(order).payment_method_id, self.bank_pm1)

    def test_close_session_rejects_missing_or_multiple_targets(self):
        other_config = self.config.copy({"name": "Other session to close"})
        other_config.open_ui()
        sessions = self.pos_session | other_config.current_session_id
        wizard = self.env["pos.close.session.wizard"].create({})

        for active_ids in (None, sessions.ids):
            with self.subTest(active_ids=active_ids), self.assertRaises(UserError):
                wizard.with_context(active_ids=active_ids).action_close_session()

        self.assertNotIn("closed", sessions.mapped("state"))

    def test_confirmation_rejects_changed_sole_customer(self):
        named_order = self._create_order(state="paid")
        anonymous_order = self._create_order(state="paid", partner_id=False)
        action = self._invoice_orders(named_order | anonymous_order)
        wizard = (
            self.env[action["res_model"]]
            .browse(action.get("res_id"))
            .with_context(action["context"])
        )
        form = Form(wizard)
        self.assertIn(self.customer.name, form.message)
        other_partner = self.env["res.partner"].create({"name": "Replacement customer"})
        named_order.partner_id = other_partner

        with self.assertRaises(UserError):
            form.save().action_confirm()

        self.assertFalse(anonymous_order.partner_id)

    def test_confirmation_round_trip_produces_paid_invoice(self):
        orders = self._create_order() | self._create_order(partner_id=False)
        for order in orders:
            self._create_payment(order).action_make_payment()
        action = self._invoice_orders(orders)
        wizard = (
            self.env[action["res_model"]]
            .browse(action.get("res_id"))
            .with_context(action["context"])
        )

        next_action = Form(wizard).save().action_confirm()
        invoice_wizard = (
            self.env[next_action["res_model"]]
            .with_context(next_action["context"])
            .create({})
        )
        invoice_wizard.action_create_invoices()

        self.assertEqual(orders.partner_id, self.customer)
        self.assertEqual(len(orders.account_move), 1)
        self.assertAlmostEqual(orders.account_move.amount_total, 200)
        self.assertAlmostEqual(orders.account_move.amount_residual, 0)

    def test_payment_rejects_already_invoiced_order(self):
        order = self._create_order()
        self._create_payment(order).action_make_payment()
        self._invoice_orders(order)
        payments = order.payment_ids

        with self.assertRaises(ValidationError):
            self._create_payment(order, amount=10).action_make_payment()

        self.assertEqual(order.payment_ids, payments)

    def test_payment_without_active_model_remains_supported(self):
        order = self._create_order()
        wizard = (
            self.env["pos.make.payment"].with_context(active_id=order.id).create({})
        )

        wizard.action_make_payment()

        self.assertEqual(order.state, "paid")
        self.assertAlmostEqual(order.amount_paid, 100)

    def test_report_default_uses_latest_start_per_config(self):
        now = self.env.cr.now()
        self.pos_session.start_at = now - timedelta(hours=12)
        self.pos_session.action_pos_session_closing_control()
        self.open_new_session().start_at = now - timedelta(hours=2)
        other_config = self.config.copy({"name": "Earlier reporting session"})
        other_config.open_ui()
        other_config.current_session_id.start_at = now - timedelta(hours=4)

        self.assertEqual(
            self.env["pos.details.wizard"]._default_start_date(),
            now - timedelta(hours=4),
        )

        other_config.current_session_id.start_at = now - timedelta(days=3)
        self.assertEqual(
            self.env["pos.details.wizard"]._default_start_date(),
            now - timedelta(hours=2),
        )

    def test_report_default_without_recent_sessions(self):
        self.pos_session.start_at = self.env.cr.now() - timedelta(days=3)

        self.assertEqual(
            self.env["pos.details.wizard"]._default_start_date(), self.env.cr.now()
        )

    def test_close_session_does_not_shrink_a_stale_selection(self):
        other_config = self.config.copy({"name": "Deleted selected session"})
        other_config.open_ui()
        other_session = other_config.current_session_id
        selected_ids = (self.pos_session | other_session).ids
        # An administrator removes one target while the user's dialog stays open.
        other_session.sudo().unlink()
        wizard = (
            self.env["pos.close.session.wizard"]
            .with_context(active_ids=selected_ids)
            .create({})
        )

        with self.assertRaises(UserError):
            wizard.action_close_session()

        self.assertEqual(self.pos_session.state, "opened")

    def test_refunds_in_separate_invoice_groups_can_be_batched(self):
        other_partner = self.env["res.partner"].create(
            {"name": "Other refund customer"}
        )
        orders = self._create_order() | self._create_order(partner_id=other_partner.id)
        refunds = self._create_invoiced_order_refunds(orders)

        self._invoice_orders(refunds)

        self.assertEqual(len(refunds.account_move), 2)
        for refund in refunds:
            self.assertEqual(
                refund.account_move.reversed_entry_id,
                refund.refunded_order_id.account_move,
            )
            self.assertEqual(refund.account_move.partner_id, refund.partner_id)
            self.assertAlmostEqual(refund.account_move.amount_total, 100)

    def test_confirmation_retains_orders_without_action_context(self):
        orders = self._create_order(state="paid") | self._create_order(
            state="paid", partner_id=False
        )
        action = self._invoice_orders(orders)
        wizard = self.env["pos.confirmation.wizard"].browse(action["res_id"])

        next_action = wizard.action_confirm()

        self.assertEqual(orders.partner_id, self.customer)
        self.assertCountEqual(next_action["context"]["active_ids"], orders.ids)

    def test_confirmation_context_cannot_replace_displayed_orders(self):
        orders = self._create_order(state="paid") | self._create_order(
            state="paid", partner_id=False
        )
        replacement = self._create_order(state="paid") | self._create_order(
            state="paid", partner_id=False
        )
        action = self._invoice_orders(orders)
        wizard = self.env["pos.confirmation.wizard"].browse(action["res_id"])

        next_action = wizard.with_context(orders=replacement.ids).action_confirm()

        self.assertEqual(orders.partner_id, self.customer)
        self.assertFalse(replacement[1].partner_id)
        self.assertCountEqual(next_action["context"]["active_ids"], orders.ids)

    def test_payment_rejects_context_for_another_model(self):
        order = self._create_order()
        wizard = self._create_payment(order)

        with self.assertRaises(UserError):
            wizard.with_context(active_model="pos.session").action_make_payment()

        self.assertFalse(order.payment_ids)

    def test_payment_defaults_handle_a_deleted_order(self):
        order = self._create_order()
        order_id = order.id
        order.sudo().unlink()

        defaults = (
            self.env["pos.make.payment"]
            .with_context(active_id=order_id)
            .default_get(
                [
                    "config_id",
                    "payment_method_id",
                    "amount",
                ]
            )
        )

        self.assertFalse(defaults.get("config_id"))
        self.assertFalse(defaults.get("payment_method_id"))
        self.assertFalse(defaults.get("amount"))

    def test_invalid_refund_group_is_rejected_before_any_invoice_is_generated(self):
        refunds = self._create_invoiced_order_refunds(
            self._create_order() | self._create_order()
        )
        other_partner = self.env["res.partner"].create(
            {"name": "Valid invoice customer"}
        )
        valid_order = self._create_order(partner_id=other_partner.id)
        self._create_payment(valid_order).action_make_payment()
        generated = []
        original_generate = type(valid_order)._generate_pos_order_invoice

        def generate_invoice(orders):
            generated.append(orders.ids)
            return original_generate(orders)

        with (
            patch.object(
                type(valid_order), "_generate_pos_order_invoice", generate_invoice
            ),
            self.assertRaises(UserError),
        ):
            self._invoice_orders(valid_order | refunds)

        self.assertEqual(generated, [])

    def test_confirmation_selection_survives_cache_invalidation(self):
        orders = self._create_order(state="paid") | self._create_order(
            state="paid", partner_id=False
        )
        action = self._invoice_orders(orders)
        wizard = self.env["pos.confirmation.wizard"].browse(action["res_id"])
        wizard.invalidate_recordset(
            ["order_ids", "unassigned_order_ids", "partner_id", "message"]
        )

        next_action = wizard.with_context(orders=[]).action_confirm()

        self.assertEqual(orders.partner_id, self.customer)
        self.assertCountEqual(next_action["context"]["active_ids"], orders.ids)

    def test_duplicate_selection_invoices_each_order_once(self):
        generated = []
        original_generate = type(self.env["pos.order"])._generate_pos_order_invoice

        def generate_invoice(orders):
            generated.append(orders.ids)
            return original_generate(orders)

        for consolidated in (False, True):
            with self.subTest(consolidated=consolidated):
                order = self._create_order()
                self._create_payment(order).action_make_payment()
                generated.clear()
                wizard = (
                    self.env["pos.make.invoice"]
                    .with_context(active_ids=[order.id, order.id], generate_pdf=False)
                    .create({"consolidated_billing": consolidated})
                )
                with patch.object(
                    type(order), "_generate_pos_order_invoice", generate_invoice
                ):
                    wizard.action_create_invoices()

                self.assertEqual(generated, [[order.id]])
                self.assertEqual(order.account_move.amount_total, 100)
                self.assertEqual(order.account_move.state, "posted")

    def test_invoice_count_uses_distinct_orders(self):
        order = self._create_order()
        wizard = (
            self.env["pos.make.invoice"]
            .with_context(active_ids=[order.id, order.id])
            .create({})
        )

        self.assertEqual(wizard.order_count, 1)

    def test_invoice_rejects_context_for_another_model(self):
        order = self._create_order()
        self._create_payment(order).action_make_payment()
        wizard = (
            self.env["pos.make.invoice"]
            .with_context(
                active_model="pos.session", active_ids=order.ids, generate_pdf=False
            )
            .create({})
        )

        with self.assertRaises(UserError):
            wizard.action_create_invoices()

        self.assertFalse(order.account_move)
        self.assertEqual(order.state, "paid")

    def test_close_session_rejects_context_for_another_model(self):
        wizard = (
            self.env["pos.close.session.wizard"]
            .with_context(active_model="pos.order", active_ids=self.pos_session.ids)
            .create({})
        )

        with self.assertRaises(UserError):
            wizard.action_close_session()

        self.assertEqual(self.pos_session.state, "opened")

    def test_confirmation_rejects_newly_anonymous_orders(self):
        named_orders = self._create_order(
            state="paid", name="Named order A"
        ) | self._create_order(state="paid", name="Named order B")
        anonymous_order = self._create_order(
            state="paid", partner_id=False, name="Anonymous order"
        )
        action = self._invoice_orders(named_orders | anonymous_order)
        wizard = self.env["pos.confirmation.wizard"].browse(action["res_id"])
        self.assertIn(anonymous_order.name, wizard.message)
        self.assertNotIn(named_orders[0].name, wizard.message)
        named_orders[0].partner_id = False

        with self.assertRaises(UserError):
            wizard.action_confirm()

        self.assertFalse(named_orders[0].partner_id)
        self.assertFalse(anonymous_order.partner_id)

    def test_confirmation_accepts_customer_already_assigned_to_displayed_order(self):
        orders = self._create_order(state="paid") | self._create_order(
            state="paid", partner_id=False
        )
        action = self._invoice_orders(orders)
        wizard = self.env["pos.confirmation.wizard"].browse(action["res_id"])
        orders[1].partner_id = self.customer

        next_action = wizard.action_confirm()

        self.assertEqual(orders.partner_id, self.customer)
        self.assertCountEqual(next_action["context"]["active_ids"], orders.ids)

    def test_invoice_action_cannot_invoice_completed_selection_again(self):
        order = self._create_order()
        self._create_payment(order).action_make_payment()
        wizard = (
            self.env["pos.make.invoice"]
            .with_context(active_ids=order.ids, generate_pdf=False)
            .create({})
        )
        wizard.action_create_invoices()
        invoice = order.account_move

        with self.assertRaises(UserError):
            wizard.action_create_invoices()

        self.assertEqual(order.account_move, invoice)
        self.assertEqual(invoice.amount_total, 100)
        self.assertEqual(invoice.state, "posted")
