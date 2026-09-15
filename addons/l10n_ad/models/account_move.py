# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ad_is_simplified = fields.Boolean(
        "Is Simplified (Andorra)",
        compute="_compute_l10n_ad_is_simplified",
        readonly=False, store=True)

    @api.depends("partner_id")
    def _compute_l10n_ad_is_simplified(self):
        simplified_partner = self.env.ref(
            "l10n_ad.partner_simplified", raise_if_not_found=False)
        for move in self:
            move.l10n_ad_is_simplified = (
                (not move.partner_id
                 and move.move_type in ("in_receipt", "out_receipt")) or
                (simplified_partner and move.partner_id == simplified_partner)
            )
