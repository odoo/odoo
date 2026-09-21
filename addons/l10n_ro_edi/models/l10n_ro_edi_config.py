from odoo import api, fields, models
from odoo.http import request
from odoo.tools.urls import urljoin as url_join


class L10nRoEdiConfig(models.Model):
    _name = "l10n_ro_edi.config"
    _description = "A company's l10n ro edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_ro_edi_client_id = fields.Char(string="eFactura Client ID")
    l10n_ro_edi_access_expiry_date = fields.Date(string="Access Token Expiry Date")
    l10n_ro_edi_refresh_expiry_date = fields.Date(string="Refresh Token Expiry Date")
    l10n_ro_edi_callback_url = fields.Char(compute="_compute_l10n_ro_edi_callback_url")
    l10n_ro_edi_test_env = fields.Boolean(
        string="Use Test Environment",
        default=True,
    )
    l10n_ro_edi_anaf_imported_inv_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Select journal for SPV imported bills",
        compute="_compute_l10n_ro_edi_anaf_imported_inv_journal_id",
        store=True,
        readonly=False,
        domain="[('type', '=', 'purchase')]",
    )

    @api.depends("company_id.country_code")
    def _compute_l10n_ro_edi_callback_url(self):
        """Callback URLs are used for generating client_id and client_secret from l10n_ro_edi's setting."""
        for config in self:
            company = config.company_id
            if company.country_code == "RO":
                config.l10n_ro_edi_callback_url = url_join(
                    request.httprequest.url_root, "l10n_ro_edi/callback/%s" % company.id
                )
            else:
                config.l10n_ro_edi_callback_url = False

    @api.depends("company_id.country_code")
    def _compute_l10n_ro_edi_anaf_imported_inv_journal_id(self):
        for config in self:
            company = config.company_id
            config.l10n_ro_edi_anaf_imported_inv_journal_id = False
            if company.country_code == "RO":
                config.l10n_ro_edi_anaf_imported_inv_journal_id = self.env[  # noqa: E8507 - one lookup per company, on its own journals
                    "account.journal"
                ].search(
                    [
                        ("type", "=", "purchase"),
                        *self.env["account.journal"]._check_company_domain(company.id),
                    ],
                    limit=1,
                )
