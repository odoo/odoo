from odoo import _, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class PosMakeInvoice(models.TransientModel):
    _name = "pos.make.invoice"
    _description = "Multiple order invoice creation"

    consolidated_billing = fields.Boolean(
        help="Create one invoice for all orders related to same customer and same invoicing address",
        default=True,
    )
    order_count = fields.Integer(compute="_compute_order_count")

    def _compute_order_count(self):
        for wizard in self:
            wizard.order_count = len(self.env.context.get("active_ids", []))

    def action_create_invoices(self):
        self.check_singleton()
        selected_orders = (
            self.env["pos.order"]
            .browse(self.env.context.get("active_ids"))
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
                _("No valid orders were selected. No new invoices could be generated")
            )

        is_single_order = len(selected_orders) == 1

        invalid_refund_orders = selected_orders.filtered(
            lambda o: o.refunded_order_id.account_move
        )
        if (not is_single_order) and invalid_refund_orders:
            order_names = "\n".join(
                [f"{o.name} ({o.pos_reference})" for o in invalid_refund_orders]
            )
            raise UserError(
                _(
                    "The following refund orders can't be part of a consolidated invoice because they refunded invoiced orders. Each refund order should be handled separately.\n\n%s",
                    order_names,
                )
            )

        invoices = self.env["account.move"]

        if not self.consolidated_billing or len(selected_orders) == 1:
            for order in selected_orders:
                invoices |= order._generate_pos_order_invoice()
        else:
            configs = selected_orders.config_id
            partners = selected_orders.partner_id
            some_order_has_no_partner = any(not o.partner_id for o in selected_orders)
            if len(configs) == 1 and len(partners) == 1 and some_order_has_no_partner:
                return {
                    "name": _("Warning"),
                    "view_mode": "form",
                    "view_id": self.env.ref(
                        "point_of_sale.view_confirm_action_wizard"
                    ).id,
                    "res_model": "pos.confirmation.wizard",
                    "target": "new",
                    "type": "ir.actions.act_window",
                    "context": {"orders": selected_orders.ids, "dialog_size": "medium"},
                }

            grouped_orders = []
            for config, config_orders in selected_orders.grouped("config_id").items():
                for partner, partner_orders in config_orders.grouped(
                    "partner_id"
                ).items():
                    if not partner:
                        raise UserError(
                            _("Kindly ensure that each order contains a customer.")
                        )

                    for user, user_orders in partner_orders.grouped("user_id").items():
                        for (
                            fiscal_position,
                            fiscal_position_orders,
                        ) in user_orders.grouped("fiscal_position_id").items():
                            grouped_orders.append(
                                (
                                    (config, partner, user, fiscal_position),
                                    fiscal_position_orders,
                                )
                            )

            dbg.logic.debug(
                "[wizard:make.invoice] %d groups by (config, partner, user, fpos): %s",
                len(grouped_orders),
                dbg.lazy(lambda: [len(orders) for _key, orders in grouped_orders]),
            )
            for _key, orders in grouped_orders:
                invoices |= orders._generate_pos_order_invoice()

        dbg.pipeline.debug(
            "[wizard:make.invoice] invoices %s for %s",
            dbg.rec(invoices),
            dbg.rec(selected_orders),
        )
        if invoices:
            return selected_orders.action_view_invoice()
        return None
