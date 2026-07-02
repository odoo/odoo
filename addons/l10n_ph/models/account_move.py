# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ph_has_discount_privilege = fields.Boolean(
        compute="_compute_l10n_ph_has_discount_privilege",
    )

    @api.depends("invoice_line_ids.l10n_ph_discount_privilege_id", "move_type")
    def _compute_l10n_ph_has_discount_privilege(self):
        for move in self:
            move.l10n_ph_has_discount_privilege = move.is_sale_document() and any(
                line.l10n_ph_discount_privilege_id
                for line in move.invoice_line_ids
                if line.display_type == "product"
            )

    def action_open_discount_privilege_wizard(self):
        self.ensure_one()
        wizard = self.env["l10n_ph.discount.privilege.wizard"].create(
            {"move_id": self.id},
        )
        return wizard._get_records_action(
            target="new",
            name=self.env._("Discount Privilege"),
        )
