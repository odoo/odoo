from odoo import fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class PosConfirmationWizard(models.TransientModel):
    _name = "pos.confirmation.wizard"
    _description = "Confirmation Wizard"

    def _get_selected_orders(self):
        if self:
            self.check_singleton()
            # the selection keeps the order it was recorded in
            return self.order_ids.sorted("id")
        selected_orders = self.env.context.get("orders")
        return self.env["pos.order"].browse(selected_orders)

    def _default_partner_id(self):
        partners = self._get_selected_orders().partner_id
        return partners if len(partners) == 1 else False

    def _default_unassigned_order_ids(self):
        return self._get_selected_orders().filtered(lambda order: not order.partner_id)

    def _default_message(self):
        selected_orders = self._get_selected_orders()
        partners = selected_orders.partner_id
        if len(partners) != 1:
            return False
        return self.env._(
            "It seems that the POS order(s) %(order_ref)s do not have a customer.\n\nWould you like to set %(customer_name)s as the customer for the selected POS order(s)?",
            order_ref=", ".join(
                selected_orders.filtered(lambda o: not o.partner_id).mapped("name")
            ),
            customer_name=partners.name,
        )

    message = fields.Text(
        default=_default_message,
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        default=_default_partner_id,
        readonly=True,
    )
    order_ids = fields.Many2many(
        comodel_name="pos.order",
        string="Orders",
        default=_get_selected_orders,
        readonly=True,
    )
    unassigned_order_ids = fields.Many2many(
        comodel_name="pos.order",
        relation="pos_confirmation_wizard_unassigned_order_rel",
        string="Orders without a Customer",
        default=_default_unassigned_order_ids,
        readonly=True,
    )

    def action_confirm(self):
        self.check_singleton()
        selected_orders = self._get_selected_orders()
        partner = selected_orders.partner_id
        anonymous_orders = selected_orders.filtered(lambda order: not order.partner_id)
        if len(partner) != 1 or len(selected_orders.config_id) != 1:
            raise UserError(
                self.env._(
                    "Select orders from one point of sale with exactly one customer to assign."
                )
            )
        newly_anonymous_orders = anonymous_orders - self.unassigned_order_ids
        if partner != self.partner_id or newly_anonymous_orders:
            dbg.logic.debug(
                "[wizard:confirmation] customer changed: displayed=%s current=%s orders=%s newly_anonymous=%s",
                dbg.rec(self.partner_id),
                dbg.rec(partner),
                dbg.rec(selected_orders),
                dbg.rec(newly_anonymous_orders),
            )
            raise UserError(
                self.env._(
                    "The customer has changed. Close this dialog and select the orders again."
                )
            )
        dbg.lifecycle.debug(
            "[wizard:confirmation] partner %s set on %s",
            dbg.rec(partner),
            dbg.rec(anonymous_orders),
        )
        anonymous_orders.write({"partner_id": partner.id})
        action = selected_orders.action_create_invoices()
        action["context"] = {
            **self.env.context,
            **action.get("context", {}),
            "active_ids": selected_orders.ids,
            "active_model": "pos.order",
        }
        return action
