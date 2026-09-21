from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = (
        "l10n_br_ie_code",
        "l10n_br_im_code",
    )

    l10n_br_config_id = fields.Many2one(
        comodel_name="l10n_br.config",
        compute="_compute_l10n_br_config_id",
        search="_search_l10n_br_config_id",
    )

    l10n_br_nire_code = fields.Char(
        related="l10n_br_config_id.l10n_br_nire_code",
        readonly=False,
    )

    def _search_l10n_br_config_id(self, operator, value):
        return self._search_config_link("l10n_br.config", operator, value)

    def _compute_l10n_br_config_id(self):
        configs = self.env["l10n_br.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_br_config_id = by_company.get(company.id, False)

    def _localization_use_documents(self):
        self.check_singleton()
        return (
            self.account_config_id.chart_template == "br"
            or super()._localization_use_documents()
        )

    def _is_latam(self):
        return (
            super()._is_latam()
            or self.account_config_id.account_fiscal_country_id.code == "BR"
        )
