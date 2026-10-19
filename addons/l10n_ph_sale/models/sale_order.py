# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_ph_has_discount_privilege = fields.Boolean(
        compute="_compute_l10n_ph_has_discount_privilege",
    )

    @api.depends("order_line.l10n_ph_discount_privilege_id", "state")
    def _compute_l10n_ph_has_discount_privilege(self):
        for order in self:
            order.l10n_ph_has_discount_privilege = order.state in ("draft", "sent") and any(
                line.l10n_ph_discount_privilege_id
                for line in order.order_line
                if not line.display_type
            )

    def action_open_discount_privilege_wizard(self):
        self.ensure_one()
        wizard = self.env["l10n_ph.discount.privilege.wizard"].create(
            {"order_id": self.id},
        )
        return wizard._get_records_action(
            target="new",
            name=self.env._("Discount Privilege"),
        )
