from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountConfig(models.Model):
    _inherit = "account.config"

    def write(self, vals):
        if (
            "account_fiscal_country_id" in vals
            and (
                german_configs := self.filtered(
                    lambda config: config.account_fiscal_country_id.code == "DE"
                )
            )
            and self.env["res.country"].browse(vals["account_fiscal_country_id"]).code
            != "DE"
            and self.env["account.move"].search_count(
                [("company_id", "in", german_configs.company_id.ids)], limit=1
            )
        ):
            raise ValidationError(_("You cannot change the fiscal country."))
        return super().write(vals)

    @api.depends("company_id.country_code")
    def _compute_force_restrictive_audit_trail(self):
        super()._compute_force_restrictive_audit_trail()
        for config in self:
            config.force_restrictive_audit_trail |= (
                config.company_id.country_code == "DE"
            )
