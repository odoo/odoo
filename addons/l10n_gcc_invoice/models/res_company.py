from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_gcc_invoice_config_id = fields.Many2one(
        comodel_name="l10n_gcc_invoice.config",
        compute="_compute_l10n_gcc_invoice_config_id",
        search="_search_l10n_gcc_invoice_config_id",
    )
    l10n_gcc_dual_language_invoice = fields.Boolean(
        related="l10n_gcc_invoice_config_id.l10n_gcc_dual_language_invoice",
    )
    l10n_gcc_country_is_gcc = fields.Boolean(compute="_compute_l10n_gcc_country_is_gcc")

    def _search_l10n_gcc_invoice_config_id(self, operator, value):
        return self._search_config_link("l10n_gcc_invoice.config", operator, value)

    def _compute_l10n_gcc_invoice_config_id(self):
        configs = self.env["l10n_gcc_invoice.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_gcc_invoice_config_id = by_company.get(company.id, False)

    @api.depends("partner_id.country_id.country_group_ids.code")
    def _compute_l10n_gcc_country_is_gcc(self):
        for record in self:
            record.l10n_gcc_country_is_gcc = (
                record.country_id and "GCC" in record.country_id.country_group_codes
            )
