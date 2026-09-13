from odoo import Command, api, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class PosMakeInvoice(models.TransientModel):
    _name = "pos.make.invoice"
    _description = "Multiple order invoice creation"

    consolidated_billing = fields.Boolean(
        default=True,
        help="Create one invoice for all orders related to same customer and same invoicing address",
    )
    order_count = fields.Integer(compute="_compute_order_count")

    @api.depends_context("active_ids")
    def _compute_order_count(self):
        for wizard in self:
            wizard.order_count = len(set(self.env.context.get("active_ids") or []))

    def action_create_invoices(self):
        self.check_singleton()
        active_model = self.env.context.get("active_model")
        if active_model and active_model != "pos.order":
            raise UserError(
                self.env._(
                    "No valid orders were selected. No new invoices could be generated"
                )
            )
        selected_orders = (
            self.env["pos.order"]
            # Recordsets preserve duplicates; invoice each selected order only once.
            .browse(list(dict.fromkeys(self.env.context.get("active_ids") or [])))
            .filtered(
                lambda o: (
                    o.invoice_state == "to_invoice"
                    and o.state not in {"draft", "cancel"}
                )
            )
        )
        dbg.lifecycle.debug(
            "[wizard:make.invoice] active_ids=%s invoiceable=%s consolidated=%s",
            self.env.context.get("active_ids"),
            dbg.rec(selected_orders),
            self.consolidated_billing,
        )
        if not selected_orders:
            raise UserError(
                self.env._(
                    "No valid orders were selected. No new invoices could be generated"
                )
            )

        if any(not order.partner_id for order in selected_orders):
            if (
                self.consolidated_billing
                and len(selected_orders.config_id) == 1
                and len(selected_orders.partner_id) == 1
            ):
                return self._open_customer_confirmation(selected_orders)
            raise UserError(
                self.env._("Kindly ensure that each order contains a customer.")
            )

        groups = self._get_invoice_groups(selected_orders)
        self._check_refund_invoice_groups(groups)
        dbg.logic.debug(
            "[wizard:make.invoice] %d invoice groups, sizes=%s",
            len(groups),
            dbg.lazy(lambda: [len(orders) for orders in groups]),
        )
        invoices = self.env["account.move"]
        for orders in groups:
            invoices |= orders._generate_pos_order_invoice()

        dbg.pipeline.debug(
            "[wizard:make.invoice] invoices %s for %s",
            dbg.rec(invoices),
            dbg.rec(selected_orders),
        )
        if invoices:
            return selected_orders.action_view_invoice()
        return None

    def _open_customer_confirmation(self, orders):
        # Persist the displayed customer and selection before opening the dialog.
        confirmation = (
            self.env["pos.confirmation.wizard"]
            .with_context(orders=orders.ids)
            .create(
                {
                    "partner_id": orders.partner_id.id,
                    "order_ids": [Command.set(orders.ids)],
                    "unassigned_order_ids": [
                        Command.set(
                            orders.filtered(lambda order: not order.partner_id).ids
                        )
                    ],
                }
            )
        )
        return {
            "name": self.env._("Warning"),
            "view_mode": "form",
            "view_id": self.env.ref("point_of_sale.view_confirm_action_wizard").id,
            "res_model": "pos.confirmation.wizard",
            "res_id": confirmation.id,
            "target": "new",
            "type": "ir.actions.act_window",
            "context": {
                **self.env.context,
                "orders": orders.ids,
                "dialog_size": "medium",
            },
        }

    def _get_invoice_groups(self, orders):
        self.check_singleton()
        if not self.consolidated_billing:
            return list(orders)
        return list(orders.grouped(self._get_invoice_group_key).values())

    def _check_refund_invoice_groups(self, groups):
        # Validate every group before posting any invoice in the batch.
        invalid_orders = self.env["pos.order"]
        for orders in groups:
            if len(orders) > 1:
                invalid_orders |= orders.filtered(
                    lambda order: order.refunded_order_id.account_move
                )
        if invalid_orders:
            raise UserError(
                self.env._(
                    "The following refund orders can't be part of a consolidated invoice because they refunded invoiced orders. Each refund order should be handled separately.\n\n%s",
                    "\n".join(
                        f"{order.name} ({order.pos_reference})"
                        for order in invalid_orders
                    ),
                )
            )

    def _get_invoice_group_key(self, order):
        """Keep every singleton consumed by the invoice preparation homogeneous."""
        return (
            order.config_id,
            order.partner_id,
            order.user_id,
            order.fiscal_position_id,
        )
