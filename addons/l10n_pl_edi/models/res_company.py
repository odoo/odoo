import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_edi_register = fields.Boolean("KSeF Integration Enabled", compute="_compute_l10n_pl_edi_register", compute_sudo=True)
    l10n_pl_edi_certificate = fields.Many2one('certificate.certificate', "KSeF Certificate", store=True, groups='base.group_system')
    l10n_pl_edi_access_token = fields.Char("KSeF Token", readonly=True, copy=False, groups='base.group_system')
    l10n_pl_edi_refresh_token = fields.Char("KSeF Token Expiration", readonly=True, copy=False, groups='base.group_system')
    l10n_pl_edi_session_id = fields.Char("Reference number", readonly=True, groups='base.group_system')
    l10n_pl_edi_session_key = fields.Binary("Session key", readonly=True, groups='base.group_system')
    l10n_pl_edi_session_iv = fields.Binary("Session iv", readonly=True, groups='base.group_system')

    # Incremental vendor bills download (KSeF export packages)
    l10n_pl_edi_bills_hwm_date = fields.Datetime(
        "KSeF Bills High Water Mark",
        help="PermanentStorage checkpoint up to which vendor bills have already been imported from KSeF.",
        readonly=True,
        copy=False,
        groups='base.group_system',
    )
    l10n_pl_edi_bills_export_ref = fields.Char(
        "KSeF Bills Export Reference",
        help="Reference number of the asynchronous KSeF export currently being processed.",
        readonly=True,
        copy=False,
        groups='base.group_system',
    )
    l10n_pl_edi_export_key = fields.Binary("KSeF Export key", readonly=True, copy=False, groups='base.group_system')
    l10n_pl_edi_export_iv = fields.Binary("KSeF Export iv", readonly=True, copy=False, groups='base.group_system')

    @api.depends("l10n_pl_edi_certificate")
    def _compute_l10n_pl_edi_register(self):
        for company in self:
            company.l10n_pl_edi_register = bool(company.l10n_pl_edi_certificate)

    @api.model
    def _cron_l10n_pl_edi_refresh_tokens(self):
        """
        Automatically performs a full KSeF authentication to renew both
        the access token and the refresh token for active companies.
        """
        companies = self.search([
            ('l10n_pl_edi_certificate', '!=', False)
        ])

        for company in companies:
            try:
                config = self.env['res.config.settings'].new({
                    'company_id': company.id,
                    'l10n_pl_edi_certificate': company.l10n_pl_edi_certificate.id,
                })

                config._l10n_pl_edi_ksef_authenticate()
                _logger.info("Successfully renewed KSeF tokens for company %s via cron.", company.name)
            except Exception:
                _logger.exception("Failed to renew KSeF token for company %s", company.name)
