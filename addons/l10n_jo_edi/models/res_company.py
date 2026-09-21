from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "l10n_jo_edi_secret_key": "l10n_jo_edi_secret_key",
    }

    l10n_jo_edi_config_id = fields.Many2one(
        comodel_name="l10n_jo_edi.config",
        compute="_compute_l10n_jo_edi_config_id",
        search="_search_l10n_jo_edi_config_id",
    )

    l10n_jo_edi_secret_key = fields.Char(
        string="JoFotara Secret Key",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        groups="base.group_system",
    )

    def _search_l10n_jo_edi_config_id(self, operator, value):
        return self._search_config_link("l10n_jo_edi.config", operator, value)

    def _compute_l10n_jo_edi_config_id(self):
        configs = self.env["l10n_jo_edi.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_jo_edi_config_id = by_company.get(company.id, False)
