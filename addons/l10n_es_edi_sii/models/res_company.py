from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_es_edi_sii_config_id = fields.Many2one(
        comodel_name="l10n_es_edi_sii.config",
        compute="_compute_l10n_es_edi_sii_config_id",
        search="_search_l10n_es_edi_sii_config_id",
    )

    # the company's own certificates, whose inverse names the company: a
    # collection it owns, not a setting the configuration keeps
    l10n_es_sii_certificate_ids = fields.One2many(
        comodel_name="certificate.certificate",
        inverse_name="company_id",
        domain=[("scope", "=", "sii")],
    )

    def _search_l10n_es_edi_sii_config_id(self, operator, value):
        return self._search_config_link("l10n_es_edi_sii.config", operator, value)

    def _compute_l10n_es_edi_sii_config_id(self):
        configs = self.env["l10n_es_edi_sii.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_es_edi_sii_config_id = by_company.get(company.id, False)
