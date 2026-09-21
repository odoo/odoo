import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"
    _CREDENTIAL_FIELDS = {
        "l10n_pl_edi_access_token": "l10n_pl_edi_access_token",
        "l10n_pl_edi_refresh_token": "l10n_pl_edi_refresh_token",
    }

    l10n_pl_edi_config_id = fields.Many2one(
        comodel_name="l10n_pl_edi.config",
        compute="_compute_l10n_pl_edi_config_id",
        search="_search_l10n_pl_edi_config_id",
    )

    l10n_pl_edi_access_token = fields.Char(
        string="KSeF Token",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        readonly=True,
        groups="base.group_system",
    )
    l10n_pl_edi_refresh_token = fields.Char(
        string="KSeF Token Expiration",
        compute="_compute_credential_doors",
        inverse="_inverse_credential_doors",
        readonly=True,
        groups="base.group_system",
    )

    def _search_l10n_pl_edi_config_id(self, operator, value):
        return self._search_config_link("l10n_pl_edi.config", operator, value)

    def _compute_l10n_pl_edi_config_id(self):
        configs = self.env["l10n_pl_edi.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_pl_edi_config_id = by_company.get(company.id, False)

    @api.model
    def _cron_l10n_pl_edi_refresh_tokens(self):
        """
        Automatically performs a full KSeF authentication to renew both
        the access token and the refresh token for active companies.
        """
        companies = self.search(
            [("l10n_pl_edi_config_id.l10n_pl_edi_certificate", "!=", False)]
        )

        for company in companies:
            try:
                config = self.env["res.config.settings"].new(
                    {
                        "company_id": company.id,
                        "l10n_pl_edi_certificate": company.l10n_pl_edi_config_id.l10n_pl_edi_certificate.id,
                    }
                )

                config._l10n_pl_edi_ksef_authenticate()
                _logger.info(
                    "Successfully renewed KSeF tokens for company %s via cron.",
                    company.name,
                )
            except Exception:
                _logger.exception(
                    "Failed to renew KSeF token for company %s", company.name
                )
