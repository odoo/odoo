# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ph_has_discount_privilege = fields.Boolean(
        compute="_compute_l10n_ph_has_discount_privilege",
    )

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        result = super()._prepare_product_base_line_for_taxes_computation(product_line)
        if product_line.l10n_ph_internal_price_unit:
            # When a discount privilege is applied the user-entered price_unit stays
            # unchanged (so the user always sees the original price), but the tax engine
            # needs the VAT-inclusive mapped price to compute taxes correctly.
            result["price_unit"] = product_line.l10n_ph_internal_price_unit
        return result

    def write(self, vals):
        if vals.get("invoice_line_ids") and any(
            move.state == "draft"
            and move.is_sale_document()
            and move.l10n_ph_has_discount_privilege
            for move in self
        ):
            existing_ids = {lid for move in self for lid in move.invoice_line_ids.ids}
            if any(
                cmd[0] == Command.CREATE
                or (cmd[0] == Command.LINK and cmd[1] not in existing_ids)
                or (cmd[0] == Command.SET and set(cmd[2]) - existing_ids)
                for cmd in vals["invoice_line_ids"]
            ):
                raise UserError(
                    self.env._(
                        "You cannot add new order lines while an SC/PWD discount privilege is applied.",
                    ),
                )
        return super().write(vals)

    @api.depends("invoice_line_ids.l10n_ph_discount_privilege_id", "move_type")
    def _compute_l10n_ph_has_discount_privilege(self):
        for move in self:
            move.l10n_ph_has_discount_privilege = move.is_sale_document() and any(
                line.l10n_ph_discount_privilege_id
                for line in move.invoice_line_ids
                if line.display_type == "product"
            )

    def _get_alerts(self):
        alerts = super()._get_alerts()
        if self.state == "draft" and self.l10n_ph_has_discount_privilege:
            alerts["l10n_ph_discount_privilege_applied"] = {
                "level": "warning",
                "message": self.env._(
                    "Discount privileges are applied. Changing discounts may cause issues.",
                ),
            }
        return alerts

    def action_open_discount_privilege_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Discount Privilege"),
            "res_model": "l10n_ph.discount_privilege.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id},
        }
