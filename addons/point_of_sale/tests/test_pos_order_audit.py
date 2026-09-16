import base64
import json
import logging
import os
import time
from copy import deepcopy
from datetime import date
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import CommonPosTest

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPosOrderAudit(CommonPosTest):
    def setUp(self):
        super().setUp()
        rounding = self.env["account.cash.rounding"].create(
            {
                "name": "Audit cash rounding",
                "rounding": 0.05,
                "rounding_method": "HALF-UP",
                "profit_account_id": self.company_data["default_account_revenue"].id,
                "loss_account_id": self.company_data["default_account_expense"].id,
            }
        )
        self.pos_config_usd.write(
            {
                "cash_rounding": True,
                "only_round_cash_method": True,
                "rounding_method": rounding.id,
            }
        )
        self.pos_config_usd.open_ui()
        self.session = self.pos_config_usd.current_session_id

    def _create_order(self, **values):
        return self.env["pos.order"].create(
            {
                "session_id": self.session.id,
                "amount_tax": 0,
                "amount_total": 0,
                "amount_paid": 0,
                "amount_return": 0,
                **values,
            }
        )

    def _create_line(self, order):
        return self.env["pos.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product_a.id,
                "qty": 1,
                "price_unit": 0,
                "price_subtotal": 0,
                "price_subtotal_incl": 0,
                "tax_ids": [Command.clear()],
            }
        )

    def _sync_values(self, order, commands):
        return {
            "uuid": order.uuid,
            "session_id": self.session.id,
            "state": "draft",
            "lines": commands,
        }

    def test_sync_rejects_multiple_origins_in_saved_refund_lines(self):
        originals = [self._create_line(self._create_order()) for _ in range(2)]
        refund = self._create_order(is_refund=True)
        first = self._create_line(refund)
        first.write({"qty": -1, "refunded_orderline_id": originals[0].id})
        second = self._create_line(refund)
        for deferred in (False, True):
            with self.subTest(deferred=deferred):
                values = self._sync_values(refund, [])
                if deferred:
                    values["relations_uuid_mapping"] = {
                        "pos.order.line": {
                            second.uuid: {"refunded_orderline_id": originals[1].uuid},
                        }
                    }
                else:
                    values["lines"] = [
                        Command.update(
                            second.id,
                            {
                                "qty": -1,
                                "refunded_orderline_id": originals[1].id,
                            },
                        )
                    ]
                with self.assertRaises(ValidationError):
                    self.env["pos.order"].sync_from_ui([values])
                self.assertFalse(second.refunded_orderline_id)

    def test_sync_refreshes_refund_origin_on_quantity_update_and_deletion(self):
        for delete in (False, True):
            with self.subTest(delete=delete):
                original = self._create_order()
                original_line = self._create_line(original)
                refund = self._create_order(is_refund=True)
                line = self._create_line(refund)
                line.write({"qty": -1, "refunded_orderline_id": original_line.id})
                command = (
                    Command.delete(line.id)
                    if delete
                    else Command.update(line.id, {"qty": -0.5})
                )
                expected_qty = 0 if delete else 0.5
                result = self.env["pos.order"].sync_from_ui(
                    [self._sync_values(refund, [command])]
                )
                _logger.debug(
                    "Refund refresh: original=%s expected_qty=%s response=%s",
                    original.id,
                    expected_qty,
                    [row["id"] for row in result["pos.order"]],
                )
                self.assertIn(original.id, [row["id"] for row in result["pos.order"]])
                refreshed = next(
                    row
                    for row in result["pos.order.line"]
                    if row["id"] == original_line.id
                )
                self.assertEqual(refreshed["refunded_qty"], expected_qty)

    def _create_rounded_paid_order(self, sign=1):
        order = self._create_order(is_refund=sign < 0)
        line = self._create_line(order)
        line.write({"qty": sign, "price_unit": 10.02})
        order._recompute_amounts()
        order.add_payment(
            {
                "pos_order_id": order.id,
                "payment_method_id": self.cash_payment_method.id,
                "amount": sign * 10,
            }
        )
        order.action_pos_order_paid()
        return order

    def test_refund_origin_reassignment_refreshes_both_originals_once(self):
        originals = [self._create_line(self._create_order()) for _ in range(2)]
        refund = self._create_order(is_refund=True)
        line = self._create_line(refund)
        line.write({"qty": -1, "refunded_orderline_id": originals[0].id})
        payload = self._sync_values(
            refund,
            [Command.update(line.id, {"refunded_orderline_id": originals[1].id})],
        )
        result = self.env["pos.order"].sync_from_ui([payload, payload])
        ids = [row["id"] for row in result["pos.order"]]
        quantities = {
            row["id"]: row["refunded_qty"] for row in result["pos.order.line"]
        }
        _logger.debug(
            "Reassigned refund response ids=%s quantities=%s", ids, quantities
        )
        self.assertEqual(
            set(ids), {refund.id, *(original.order_id.id for original in originals)}
        )
        self.assertEqual(len(ids), 3)
        self.assertEqual(quantities[originals[0].id], 0)
        self.assertEqual(quantities[originals[1].id], 1)

    def test_paid_cash_payment_can_switch_to_exact_bank_settlement(self):
        for sign in (1, -1):
            with self.subTest(sign=sign):
                order = self._create_rounded_paid_order(sign)
                order.write(
                    {
                        "payment_ids": [
                            Command.update(
                                order.payment_ids.id,
                                {
                                    "payment_method_id": self.bank_payment_method.id,
                                    "amount": sign * 10.02,
                                },
                            )
                        ]
                    }
                )
                self.assertEqual(
                    order.payment_ids.payment_method_id, self.bank_payment_method
                )
                self.assertEqual(order.amount_paid, sign * 10.02)
                self.assertTrue(order._is_payment_amount_valid())

    def test_rounded_paid_payment_updates_preserve_valid_settlement(self):
        for sign in (1, -1):
            for state in ("paid", "done"):
                with self.subTest(sign=sign, state=state):
                    order = self._create_rounded_paid_order(sign)
                    order.state = state
                    before = order.message_ids
                    order.write(
                        {
                            "payment_ids": [
                                Command.update(
                                    order.payment_ids.id, {"name": "terminal reference"}
                                )
                            ]
                        }
                    )
                    self.assertEqual(order.amount_paid, sign * 10)
                    self.assertEqual(order.state, state)
                    self.assertFalse(order.message_ids - before)

    def test_paid_refund_cannot_be_edited_to_underpay_customer(self):
        for state in ("paid", "done"):
            with self.subTest(state=state):
                order = self._create_rounded_paid_order(-1)
                order.state = state
                with self.assertRaises(UserError):
                    order.write(
                        {
                            "payment_ids": [
                                Command.update(order.payment_ids.id, {"amount": -9})
                            ]
                        }
                    )
                self.assertEqual(order.amount_paid, -10)

    def test_paid_payment_edits_still_reject_underpayment_and_warn_overpayment(self):
        for sign in (1, -1):
            with self.subTest(sign=sign):
                order = self._create_rounded_paid_order(sign)
                with self.assertRaises(UserError):
                    order.write(
                        {
                            "payment_ids": [
                                Command.update(
                                    order.payment_ids.id, {"amount": sign * 9}
                                )
                            ]
                        }
                    )
                previous = order.message_ids
                values = {
                    "payment_ids": [
                        Command.update(order.payment_ids.id, {"amount": sign * 11})
                    ]
                }
                if sign < 0:
                    # Preserve the existing rejection of excessive refund payments.
                    with self.assertRaises(UserError):
                        order.write(values)
                else:
                    order.write(values)
                    self.assertIn(
                        "higher than the total", (order.message_ids - previous).body
                    )

    def test_paid_cash_rounding_cannot_be_kept_after_switching_to_bank(self):
        for sign in (1, -1):
            with self.subTest(sign=sign):
                order = self._create_rounded_paid_order(sign)
                with self.assertRaises(UserError):
                    order.write(
                        {
                            "payment_ids": [
                                Command.update(
                                    order.payment_ids.id,
                                    {
                                        "payment_method_id": self.bank_payment_method.id,
                                    },
                                )
                            ]
                        }
                    )
                self.assertEqual(
                    order.payment_ids.payment_method_id, self.cash_payment_method
                )

    def test_refund_eligibility_uses_product_quantity_precision(self):
        order = self._create_order()
        exhausted = self._create_line(order)
        exhausted.qty = 0.8
        available = self._create_line(order)
        prior_refund = self._create_order(is_refund=True)
        for qty in (-0.1, -0.7):
            prior_line = self._create_line(prior_refund)
            prior_line.write({"qty": qty, "refunded_orderline_id": exhausted.id})
        self.assertTrue(order.has_refundable_lines)

        refund = order._refund()

        _logger.debug(
            "Precision refund: original=%s refunded=%s new=%s",
            exhausted.qty,
            exhausted.refunded_qty,
            refund.lines.mapped("qty"),
        )
        self.assertEqual(refund.lines.refunded_orderline_id, available)
        self.assertEqual(refund.lines.qty, -1)
        self.assertFalse(order.has_refundable_lines)

    def test_cancelled_refund_restores_fractional_quantity_and_lots(self):
        order = self._create_order()
        line = self._create_line(order)
        line.qty = 0.3
        lots = self.env["pos.pack.operation.lot"].create(
            [
                {"pos_order_line_id": line.id, "lot_name": name}
                for name in ("AUDIT-LOT-1", "AUDIT-LOT-2")
            ]
        )
        prior = order._refund()
        self.assertFalse(order.has_refundable_lines)
        prior.action_pos_order_cancel()
        self.assertTrue(order.has_refundable_lines)

        refund = order._refund()

        self.assertAlmostEqual(refund.lines.qty, -0.3)
        self.assertEqual(
            refund.lines.pack_lot_ids.mapped("lot_name"), lots.mapped("lot_name")
        )
        self.assertFalse(refund.lines.pack_lot_ids & lots)
        self.assertEqual(lots.pos_order_line_id, line)

    def test_refund_form_action_requires_one_order_before_creating_records(self):
        orders = self._create_order() | self._create_order()
        for order in orders:
            self._create_line(order)
        before = self.session.order_ids
        with self.assertRaises(ValueError):
            orders.action_refund()
        self.assertEqual(self.session.order_ids, before)

    def test_preparation_payload_validation_on_create_and_write(self):
        order = self._create_order()
        invalid_payloads = (
            "{",
            "[]",
            "null",
            "1",
            '{"metadata": []}',
            '{"metadata": {"serverDate": "not-a-date"}}',
            '{"metadata": {"serverDate": 42}}',
            '{"metadata": {"serverDate": []}}',
            '{"metadata": {"serverDate": {}}}',
            '{"metadata": {"serverDate": 0}}',
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                _logger.debug("Rejecting malformed preparation payload %s", payload)
                with self.assertRaises(ValidationError):
                    self._create_order(last_order_preparation_change=payload)
                with self.assertRaises(ValidationError):
                    order.write({"last_order_preparation_change": payload})
                self.assertFalse(order.last_order_preparation_change)

    def test_preparation_validation_preserves_optional_and_extension_fields(self):
        for payload in (
            False,
            "",
            "{}",
            '{"metadata": null}',
            '{"metadata": {"serverDate": false, "extension": 1}}',
            '{"metadata": {"serverDate": "2026-09-13 12:00:00"}, "extension": [1]}',
        ):
            with self.subTest(payload=payload):
                order = self._create_order(last_order_preparation_change=payload)
                self.assertEqual(
                    order.last_order_preparation_change or False, payload or False
                )

    def test_sync_rejects_invalid_preparation_before_merging(self):
        for stored in (False, '{"metadata": {"serverDate": "2026-09-13 12:00:00"}}'):
            for state in ("draft", "paid"):
                with self.subTest(stored=stored, state=state):
                    order = self._create_order(
                        last_order_preparation_change=stored, state=state
                    )
                    values = self._sync_values(order, [])
                    values["last_order_preparation_change"] = '{"metadata": []}'
                    with self.assertRaises(ValidationError):
                        self.env["pos.order"].sync_from_ui([values])
                    self.assertEqual(order.last_order_preparation_change, stored)

    def test_receipt_attachments_are_batched_and_keep_payloads(self):
        order = self._create_order()
        order.account_move = self.env["account.move"].create(
            {"move_type": "out_invoice", "partner_id": self.partner_a.id}
        )
        attachment_model = self.env["ir.attachment"]
        original_create = type(attachment_model).create
        batches = []

        def record_create(records, values):
            batch = values if isinstance(values, list) else [values]
            batches.append(len(batch))
            return original_create(records, values)

        with (
            patch.object(type(attachment_model), "create", record_create),
            patch.object(
                type(self.env["ir.actions.report"]),
                "_render_qweb_pdf",
                return_value=(b"%PDF-audit", "pdf"),
            ) as render,
        ):
            commands = order._create_mail_attachments(
                "Audit", base64.b64encode(b"receipt"), base64.b64encode(b"basic")
            )
        attachments = attachment_model.browse([command[1] for command in commands])
        _logger.debug(
            "Receipt attachment batches=%s records=%s", batches, attachments.ids
        )
        self.assertEqual(batches, [3])
        self.assertEqual(
            attachments.mapped("name"),
            ["Receipt-Audit.jpg", "Receipt-Audit-1.jpg", "Audit.pdf"],
        )
        self.assertEqual(
            [base64.b64decode(item.datas) for item in attachments],
            [b"receipt", b"basic", b"%PDF-audit"],
        )
        self.assertEqual(attachments.mapped("res_model"), ["pos.order"] * 3)
        self.assertEqual(attachments.mapped("res_id"), [order.id] * 3)
        render.assert_called_once_with(
            "account.account_invoices", order.account_move.id
        )

    def test_receipt_without_invoice_or_basic_image_has_one_attachment(self):
        order = self._create_order()
        commands = order._create_mail_attachments(
            "Audit", base64.b64encode(b"receipt"), False
        )
        self.assertEqual(len(commands), 1)
        attachment = self.env["ir.attachment"].browse(commands[0][1])
        self.assertEqual(attachment.res_id, order.id)
        self.assertEqual(base64.b64decode(attachment.datas), b"receipt")

    def test_sync_preserves_payload_for_extensions_and_retries(self):
        order = self._create_order()
        line = self._create_line(order)
        values = self._sync_values(
            order, [[Command.UPDATE, line.id, {"customer_note": "Updated"}]]
        )
        expected = deepcopy(values)

        self.env["pos.order"].sync_from_ui([values])

        self.assertEqual(line.customer_note, "Updated")
        self.assertEqual(values, expected)
        self.env["pos.order"].sync_from_ui([values])
        self.assertEqual(order.lines, line)

    def test_retry_accepts_immutable_create_commands(self):
        order = self._create_order()
        line = self._create_line(order)
        values = self._sync_values(
            order,
            [Command.create({"uuid": line.uuid, "customer_note": "Retried"})],
        )

        self.env["pos.order"].sync_from_ui([values])

        self.assertEqual(order.lines, line)
        self.assertEqual(line.customer_note, "Retried")

    def test_uuid_mapping_links_combo_lines(self):
        order = self._create_order()
        parent = self._create_line(order)
        child = self._create_line(order)
        values = self._sync_values(order, [])
        values["relations_uuid_mapping"] = {
            "pos.order.line": {
                child.uuid: {"combo_parent_id": parent.uuid},
                parent.uuid: {"combo_line_ids": [child.uuid]},
            }
        }

        self.env["pos.order"].sync_from_ui([values])

        self.assertEqual(child.combo_parent_id, parent)
        self.assertEqual(parent.combo_line_ids, child)

    def test_uuid_relations_share_nonempty_comodel_lookup(self):
        order = self._create_order()
        parent, child, grandchild = [self._create_line(order) for _ in range(3)]
        original_search = type(child).search
        searches = []

        def record_search(records, domain, *args, **kwargs):
            searches.append(domain)
            return original_search(records, domain, *args, **kwargs)

        self.env.flush_all()
        before = self.env.cr.sql_statement_count
        with patch.object(type(child), "search", record_search):
            order._link_uuid_relations(
                {
                    "pos.order.line": {
                        child.uuid: {
                            "combo_parent_id": parent.uuid,
                            "combo_line_ids": [grandchild.uuid],
                        }
                    }
                }
            )
        _logger.debug(
            "Nonempty UUID relations: searches=%s SQL statements=%s",
            len(searches),
            self.env.cr.sql_statement_count - before,
        )
        self.assertEqual(child.combo_parent_id, parent)
        self.assertEqual(child.combo_line_ids, grandchild)
        self.assertEqual(grandchild.combo_parent_id, child)
        self.assertEqual(len(searches), 2)

    def test_empty_preparation_change_keeps_server_payload(self):
        order = self._create_order(
            last_order_preparation_change=json.dumps(
                {"metadata": {"serverDate": "2026-09-13 12:00:00"}}
            )
        )
        for incoming in (False, None, "", "{}"):
            with self.subTest(incoming=incoming):
                values = {"last_order_preparation_change": incoming}
                order._keep_newest_preparation_change(values)
                self.assertEqual(
                    values["last_order_preparation_change"],
                    order.last_order_preparation_change,
                )

    def test_undated_preparation_change_keeps_dated_server_payload(self):
        order = self._create_order(
            last_order_preparation_change=json.dumps(
                {"metadata": {"serverDate": "2026-09-13 12:00:00"}}
            )
        )
        values = {"last_order_preparation_change": '{"metadata": {"changes": 1}}'}

        order._keep_newest_preparation_change(values)

        self.assertEqual(
            values["last_order_preparation_change"], order.last_order_preparation_change
        )

    def test_dated_preparation_change_replaces_undated_server_payload(self):
        order = self._create_order(
            last_order_preparation_change='{"metadata": {"changes": 1}}'
        )
        values = {
            "last_order_preparation_change": json.dumps(
                {"metadata": {"serverDate": "2026-09-13 12:00:00"}, "lines": {"new": 1}}
            )
        }

        order._keep_newest_preparation_change(values)

        self.assertEqual(
            json.loads(values["last_order_preparation_change"])["lines"], {"new": 1}
        )

    def test_card_underpayment_cannot_use_cash_only_tolerance(self):
        order = self._create_order(amount_total=10.02)
        order.add_payment(
            {
                "pos_order_id": order.id,
                "payment_method_id": self.bank_payment_method.id,
                "amount": 10,
            }
        )
        _logger.debug(
            "Card-only payment: total=%s paid=%s", order.amount_total, order.amount_paid
        )

        with self.assertRaises(UserError):
            order.action_pos_order_paid()

        self.assertEqual(order.state, "draft")

    def test_cash_payment_can_use_cash_rounding(self):
        order = self._create_order(amount_total=10.02)
        order.add_payment(
            {
                "pos_order_id": order.id,
                "payment_method_id": self.cash_payment_method.id,
                "amount": 10,
            }
        )

        order.action_pos_order_paid()

        self.assertEqual(order.state, "paid")

    def test_zero_payment_edit_is_in_chatter(self):
        order = self._create_order()
        order.add_payment(
            {
                "pos_order_id": order.id,
                "payment_method_id": self.cash_payment_method.id,
                "amount": 5,
            }
        )
        previous_messages = order.message_ids

        order.write(
            {"payment_ids": [Command.update(order.payment_ids.id, {"amount": 0})]}
        )

        messages = order.message_ids - previous_messages
        self.assertEqual(len(messages), 1)
        self.assertIn("changed from", messages.body)
        self.assertEqual(order.amount_paid, 0)

    def test_invoice_date_treats_order_datetime_as_utc(self):
        order = self._create_order(
            partner_id=self.partner_mobt.id,
            date_order=fields.Datetime.to_datetime("2026-09-13 01:00:00"),
        ).with_context(tz="America/Mexico_City")
        try:
            with patch.dict(os.environ, TZ="America/Los_Angeles"):
                time.tzset()
                values = order._prepare_invoice_vals()
        finally:
            time.tzset()

        self.assertEqual(values["invoice_date"], date(2026, 9, 12))

    def test_cost_uses_order_company_when_active_company_differs(self):
        order = self._create_order()
        line = self._create_line(order)
        other_company = self.env["res.company"].create(
            {"name": "Other costing company"}
        )
        self.env.user.sudo().company_ids += other_company
        line.product_id.with_company(order.company_id).standard_price = 7
        line.product_id.with_company(other_company).standard_price = 17

        line.sudo().with_company(other_company)._update_total_cost(
            self.env["stock.move"]
        )

        self.assertEqual(line.total_cost, 7)
        self.assertEqual(line.price_cost, 7)

    def test_ship_later_refund_does_not_convert_foreign_cost_twice(self):
        company = self.env.company
        euro = self.env.ref("base.EUR")
        self.env["res.currency.rate"].create(
            {
                "currency_id": euro.id,
                "company_id": company.id,
                "name": fields.Date.today(),
                "rate": 2,
            }
        )
        self.pos_config_eur.open_ui()
        order = self._create_order(session_id=self.pos_config_eur.current_session_id.id)
        original = self._create_line(order)
        original.product_id = self.test_product_order
        original.qty = 2
        original.product_id.standard_price = 10
        original._update_total_cost(self.env["stock.move"])
        self.assertEqual(original.total_cost, 40)
        # Legacy lines can carry a total without a recorded source unit cost.
        original.price_cost = 0
        refund = self._create_order(
            session_id=order.session_id.id,
            shipping_date=fields.Date.today(),
            is_refund=True,
        )
        line = self._create_line(refund)
        line.write(
            {
                "product_id": original.product_id.id,
                "qty": -1,
                "refunded_orderline_id": original.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "product_id": line.product_id.id,
                "product_uom_id": line.product_uom_id.id,
                "product_uom_qty": 1,
                "location_id": self.env.ref("stock.stock_location_customers").id,
                "location_dest_id": self.company_data[
                    "default_warehouse"
                ].lot_stock_id.id,
            }
        )

        line._update_total_cost(move)

        self.assertEqual(line.total_cost, -20)
        self.assertEqual(line.price_cost, 10)

    def test_margin_percentage_refreshes_when_margin_stays_constant(self):
        order = self._create_order()
        line = self._create_line(order)
        line.write(
            {"price_subtotal": 100, "total_cost": 50, "is_total_cost_computed": True}
        )
        self.assertEqual(order.margin, 50)
        self.assertEqual(order.margin_percent, 0.5)

        line.write({"price_subtotal": 200, "total_cost": 150})

        self.assertEqual(order.margin, 50)
        self.assertEqual(order.margin_percent, 0.25)

    def test_fresh_json_retry_does_not_duplicate_records(self):
        order = self._create_order()
        line = self._create_line(order)
        payload = json.dumps(
            self._sync_values(
                order, [[0, 0, {"uuid": line.uuid, "customer_note": "Fresh request"}]]
            )
        )

        for _attempt in range(2):
            self.env["pos.order"].sync_from_ui([json.loads(payload)])

        self.assertEqual(order.lines, line)
        self.assertEqual(line.customer_note, "Fresh request")

    def test_payment_retry_accepts_tuple_commands(self):
        order = self._create_order()
        order.add_payment(
            {
                "pos_order_id": order.id,
                "payment_method_id": self.cash_payment_method.id,
                "amount": 0,
            }
        )
        payment = order.payment_ids
        values = self._sync_values(order, [])
        values["payment_ids"] = [Command.create({"uuid": payment.uuid, "amount": 1})]
        expected = deepcopy(values)

        self.env["pos.order"].sync_from_ui([values])

        self.assertEqual(order.payment_ids, payment)
        self.assertEqual(payment.amount, 1)
        self.assertEqual(values, expected)

    def test_preparation_conflicts_through_finalized_order_sync(self):
        server = json.dumps(
            {"metadata": {"serverDate": "2026-09-13 12:00:00"}, "lines": {"server": 1}}
        )
        for client_date, expected_key in (
            ("2026-09-13 11:59:59", "server"),
            ("2026-09-13 12:00:00", "client"),
            ("2026-09-13 12:00:01", "client"),
        ):
            with self.subTest(client_date=client_date):
                order = self._create_order(
                    state="paid", last_order_preparation_change=server
                )
                values = self._sync_values(order, [])
                values["last_order_preparation_change"] = json.dumps(
                    {
                        "metadata": {"serverDate": client_date},
                        "lines": {"client": 1},
                    }
                )
                expected = deepcopy(values)

                with freeze_time("2026-09-13 12:01:00"):
                    self.env["pos.order"].sync_from_ui([values])

                self.assertEqual(order.state, "paid")
                self.assertEqual(
                    json.loads(order.last_order_preparation_change)["lines"],
                    {expected_key: 1},
                )
                self.assertEqual(values, expected)

    def test_cash_only_rounding_through_sync_with_real_totals(self):
        self.product_a.type = "service"
        for sign in (1, -1):
            for method in (self.cash_payment_method, self.bank_payment_method):
                with self.subTest(sign=sign, method=method.name):
                    order = self._create_order(is_refund=sign < 0)
                    line = self._create_line(order)
                    line.write({"qty": sign, "price_unit": 10.02})
                    order._recompute_amounts()
                    self.assertEqual(order.amount_total, sign * 10.02)
                    values = self._sync_values(order, [])
                    values.update(
                        {
                            "state": "paid",
                            "payment_ids": [
                                Command.create(
                                    {
                                        "payment_method_id": method.id,
                                        "amount": sign * 10,
                                    }
                                )
                            ],
                        }
                    )

                    if method == self.bank_payment_method:
                        with self.assertRaises(UserError), self.env.cr.savepoint():
                            self.env["pos.order"].sync_from_ui([values])
                        self.assertEqual(order.state, "draft")
                        self.assertFalse(order.payment_ids)
                    else:
                        self.env["pos.order"].sync_from_ui([values])
                        self.assertEqual(order.state, "paid")

    def test_zero_cash_line_preserves_explicit_rounding_intent(self):
        order = self._create_order(amount_total=10.02)
        for method, amount in (
            (self.bank_payment_method, 10),
            (self.cash_payment_method, 0),
        ):
            order.add_payment(
                {
                    "pos_order_id": order.id,
                    "payment_method_id": method.id,
                    "amount": amount,
                }
            )

        order.action_pos_order_paid()

        self.assertEqual(order.state, "paid")

    def test_cash_payment_can_round_the_entire_order_to_zero(self):
        self.session.set_opening_control(0, None)
        order = self._create_order()
        self.product_a.type = "service"
        line = self._create_line(order)
        line.price_unit = 0.02
        order._recompute_amounts()
        self.assertEqual(order.amount_total, 0.02)
        values = self._sync_values(order, [])
        values.update(
            {
                "state": "paid",
                "payment_ids": [
                    Command.create(
                        {
                            "payment_method_id": self.cash_payment_method.id,
                            "amount": 0,
                        }
                    )
                ],
            }
        )

        self.env["pos.order"].sync_from_ui([values])

        self.assertEqual(order.state, "paid")
        self.assertEqual(order.amount_paid, 0)
        self.assertEqual(order.payment_ids.payment_method_id, self.cash_payment_method)

        self.session.action_pos_session_closing_control()

        self.assertEqual(self.session.state, "closed")
        self.assertEqual(self.session.move_id.state, "posted")

    def test_zero_edit_with_method_change_preserves_both_history_values(self):
        order = self._create_order()
        order.add_payment(
            {
                "pos_order_id": order.id,
                "payment_method_id": self.cash_payment_method.id,
                "amount": 5,
            }
        )
        before = order.message_ids

        order.write(
            {
                "payment_ids": [
                    Command.update(
                        order.payment_ids.id,
                        {
                            "amount": 0,
                            "payment_method_id": self.bank_payment_method.id,
                        },
                    )
                ]
            }
        )

        messages = order.message_ids - before
        self.assertEqual(len(messages), 1)
        self.assertIn(self.cash_payment_method.name, messages.body)
        self.assertIn(self.bank_payment_method.name, messages.body)
        self.assertIn("and from", messages.body)
        self.assertIn("0.00", messages.body)

    def test_invoice_date_under_normal_utc_process(self):
        order = self._create_order(
            partner_id=self.partner_mobt.id, date_order="2026-09-13 01:00:00"
        )
        for timezone, expected in (
            ("UTC", date(2026, 9, 13)),
            ("America/Mexico_City", date(2026, 9, 12)),
            ("Asia/Tokyo", date(2026, 9, 13)),
        ):
            with self.subTest(timezone=timezone):
                self.assertEqual(os.environ.get("TZ"), "UTC")
                self.assertEqual(
                    order.with_context(tz=timezone)._prepare_invoice_vals()[
                        "invoice_date"
                    ],
                    expected,
                )

    def test_margin_percentage_survives_flush_and_cache_invalidation(self):
        order = self._create_order()
        line = self._create_line(order)
        line.write(
            {"price_subtotal": 100, "total_cost": 50, "is_total_cost_computed": True}
        )
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(order.margin_percent, 0.5)

        line.write({"price_subtotal": 200, "total_cost": 150})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(order.margin, 50)
        self.assertEqual(order.margin_percent, 0.25)

    def test_uuid_relations_preserve_unmapped_and_missing_targets(self):
        order = self._create_order()
        parent = self._create_line(order)
        child = self._create_line(order)
        other = self._create_line(order)
        child.combo_parent_id = parent
        mapping = {
            "pos.order.line": {
                "missing-owner": {"combo_parent_id": parent.uuid},
                child.uuid: {"combo_parent_id": "missing-target"},
                parent.uuid: {"combo_line_ids": [other.uuid, "missing-target"]},
            }
        }

        values = self._sync_values(order, [])
        values["relations_uuid_mapping"] = mapping
        self.env["pos.order"].sync_from_ui([values])

        self.assertFalse(child.combo_parent_id)
        self.assertEqual(parent.combo_line_ids, other)

    def test_uuid_relations_batch_owner_writes(self):
        order = self._create_order()
        parent = self._create_line(order)
        children = self.env["pos.order.line"].create(
            [
                {
                    "order_id": order.id,
                    "product_id": self.product_a.id,
                    "price_subtotal": 0,
                    "price_subtotal_incl": 0,
                }
                for _ in range(20)
            ]
        )
        values = self._sync_values(order, [])
        values["relations_uuid_mapping"] = {
            "pos.order.line": {
                child.uuid: {"combo_parent_id": parent.uuid, "combo_line_ids": []}
                for child in children
            }
        }
        write_batches = []
        uuid_searches = []
        original_write = type(children).write
        original_search = type(children).search

        def record_search(records, domain, *args, **kwargs):
            if len(domain) == 1 and domain[0][0] == "uuid":
                uuid_searches.append(domain)
            return original_search(records, domain, *args, **kwargs)

        def record_write(records, vals):
            if "combo_parent_id" in vals or "combo_line_ids" in vals:
                write_batches.append((records.ids, sorted(vals)))
            return original_write(records, vals)

        started = time.perf_counter()
        statements_before = self.env.cr.sql_statement_count
        with (
            patch.object(type(children), "write", record_write),
            patch.object(type(children), "search", record_search),
        ):
            self.env["pos.order"].sync_from_ui([values])

        _logger.debug(
            "UUID batching: owners=%d writes=%d statements=%d elapsed_ms=%.2f batches=%s",
            len(children),
            len(write_batches),
            self.env.cr.sql_statement_count - statements_before,
            (time.perf_counter() - started) * 1000,
            write_batches,
        )
        self.assertEqual(parent.combo_line_ids, children)
        self.assertLessEqual(len(write_batches), len(children))
        _logger.debug("UUID relation searches: %s", uuid_searches)
        self.assertLessEqual(len(uuid_searches), 2)

    def test_refund_cost_preserves_saved_unit_cost_after_rate_correction(self):
        euro = self.env.ref("base.EUR")
        rate = self.env["res.currency.rate"].create(
            {
                "currency_id": euro.id,
                "company_id": self.env.company.id,
                "name": "2026-09-01",
                "rate": 2,
            }
        )
        self.env["res.currency.rate"].create(
            {
                "currency_id": euro.id,
                "company_id": self.env.company.id,
                "name": "2026-09-13",
                "rate": 3,
            }
        )
        self.pos_config_eur.open_ui()
        original = self._create_order(
            session_id=self.pos_config_eur.current_session_id.id,
            date_order="2026-09-01 12:00:00",
        )
        original_line = self._create_line(original)
        original_line.product_id = self.test_product_order
        original_line.product_id.standard_price = 10
        original_line._update_total_cost(self.env["stock.move"])
        self.assertEqual(original_line.total_cost, 20)
        self.assertEqual(original_line.price_cost, 10)
        rate.rate = 4
        refund = self._create_order(
            session_id=original.session_id.id,
            date_order="2026-09-13 12:00:00",
            shipping_date="2026-09-14",
            is_refund=True,
        )
        line = self._create_line(refund)
        line.write(
            {
                "product_id": original_line.product_id.id,
                "qty": -1,
                "refunded_orderline_id": original_line.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "product_id": line.product_id.id,
                "product_uom_id": line.product_uom_id.id,
                "product_uom_qty": 1,
                "location_id": self.env.ref("stock.stock_location_customers").id,
                "location_dest_id": self.company_data[
                    "default_warehouse"
                ].lot_stock_id.id,
            }
        )

        line._update_total_cost(move)

        self.assertEqual(line.price_cost, 10)
        self.assertEqual(line.total_cost, -30)
