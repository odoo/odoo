from odoo import api, fields, models


class MixinFiscalCountryCodes(models.AbstractModel):
    _name = "mixin.fiscal.country.codes"
    _description = "Fiscal Country Codes"

    fiscal_country_codes = fields.Char(compute="_compute_fiscal_country_codes")

    def _get_fiscal_country_companies(self):
        self.check_singleton()
        return self.env.companies

    @api.depends_context("allowed_company_ids")
    def _compute_fiscal_country_codes(self):
        for record in self:
            record.fiscal_country_codes = ",".join(
                sorted(
                    record._get_fiscal_country_companies().mapped(
                        "account_config_id.account_fiscal_country_id.code"
                    )
                )
            )
