# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_lk_vat_registered = fields.Boolean(
        string="VAT Registered?",
        help="Indicates if this partner is registered for VAT in Sri Lanka. "
        "Tax invoices can only be issued when both supplier and buyer are VAT registered.",
        compute="_compute_l10n_lk_vat_registered",
        store=True,
        readonly=False,
    )

    @api.depends("vat", "country_id")
    def _compute_l10n_lk_vat_registered(self):
        for partner in self:
            if partner.country_id.code != "LK":
                partner.l10n_lk_vat_registered = False
            else:
                vat_digits = "".join(ch for ch in (partner.vat or "") if ch.isdigit())
                partner.l10n_lk_vat_registered = len(vat_digits) >= 13 and vat_digits[-4:] == "7000"
