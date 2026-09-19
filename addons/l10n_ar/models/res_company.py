from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = (
        "l10n_ar_gross_income_number",
        "l10n_ar_gross_income_type",
        "l10n_ar_afip_responsibility_type_id",
    )

    l10n_ar_company_requires_vat = fields.Boolean(
        string="Company Requires Vat?",
        compute="_compute_l10n_ar_company_requires_vat",
    )
    l10n_ar_afip_start_date = fields.Date(string="Activities Start")

    @api.onchange("country_id")
    def onchange_country(self):
        """Argentinean companies use round_globally as tax_calculation_rounding_method"""
        for rec in self.filtered(lambda x: x.country_id.code == "AR"):
            rec.account_config_id.tax_calculation_rounding_method = "round_globally"

    @api.depends("l10n_ar_afip_responsibility_type_id")
    def _compute_l10n_ar_company_requires_vat(self):
        recs_requires_vat = self.filtered(
            lambda x: x.l10n_ar_afip_responsibility_type_id.code == "1"
        )
        recs_requires_vat.l10n_ar_company_requires_vat = True
        remaining = self - recs_requires_vat
        remaining.l10n_ar_company_requires_vat = False

    def _localization_use_documents(self):
        """Argentinean localization use documents"""
        self.check_singleton()
        return (
            self.account_config_id.chart_template in {"ar_base", "ar_ex", "ar_ri"}
            or super()._localization_use_documents()
        )

    def write(self, vals):
        if "l10n_ar_afip_responsibility_type_id" in vals:
            for company in self:
                if (
                    vals["l10n_ar_afip_responsibility_type_id"]
                    != company.l10n_ar_afip_responsibility_type_id.id
                    and company.sudo()._existing_accounting()
                ):
                    raise UserError(
                        _(
                            "Could not change the ARCA Responsibility of this company because there are already accounting entries."
                        )
                    )

        return super().write(vals)

    def _is_latam(self):
        return super()._is_latam() or self.country_code == "AR"
