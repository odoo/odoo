from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_hu_group_vat = fields.Char(
        string="Group Tax ID",
        size=13,
        index=True,
        help="If this company belongs to a VAT group, indicate the group's VAT number here.",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            "l10n_hu_group_vat",
        ]

    def _check_vies(self, vat):
        """Convert back the hungarian format to EU format: 12345678-1-12 => HU12345678"""
        if self.country_code == "HU" and vat and not vat.upper().startswith("HU"):
            vat = f"HU{vat[:8]}"
        return super()._check_vies(vat)
