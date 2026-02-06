# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

CERT_EXPIRY_WARN_DAYS = 30
RANGE_LOW_THRESHOLD = 100


class ResCompany(models.Model):
    _inherit = 'res.company'

    # -- DIAN Software Registration --
    l10n_co_edi_software_id = fields.Char(
        string='DIAN Software ID',
        help='Software identifier assigned by DIAN during electronic invoicing enablement.',
    )
    l10n_co_edi_software_pin = fields.Char(
        string='DIAN Software PIN',
        groups='base.group_system',
        help='Software PIN assigned by DIAN. Used in CUDE computation and web service auth.',
    )
    l10n_co_edi_test_mode = fields.Boolean(
        string='DIAN Test Mode',
        default=True,
        help='When enabled, documents are sent to DIAN test environment (habilitacion). '
             'Disable for production.',
    )

    # -- Digital Certificate --
    l10n_co_edi_certificate = fields.Binary(
        string='Digital Certificate (.p12)',
        groups='base.group_system',
        help='ONAC-accredited digital certificate in PKCS#12 (.p12/.pfx) format.',
    )
    l10n_co_edi_certificate_filename = fields.Char(
        string='Certificate Filename',
    )
    l10n_co_edi_certificate_password = fields.Char(
        string='Certificate Password',
        groups='base.group_system',
        help='Password to unlock the digital certificate.',
    )
    l10n_co_edi_certificate_expiry = fields.Date(
        string='Certificate Expiry Date',
        help='Expiration date of the digital certificate. Set automatically on upload.',
    )

    # -- Company Tax Classification --
    l10n_co_edi_gran_contribuyente = fields.Boolean(
        string='Gran Contribuyente',
        help='Check if the company is classified as Gran Contribuyente by DIAN.',
    )
    l10n_co_edi_autorretenedor = fields.Boolean(
        string='Autorretenedor',
        help='Check if the company is designated as a self-withholding agent by DIAN.',
    )
    l10n_co_edi_tax_regime = fields.Selection(
        selection=[
            ('common', 'Regimen Comun (Responsable de IVA)'),
            ('simple', 'Regimen Simple de Tributacion (SIMPLE)'),
            ('not_responsible', 'No Responsable de IVA'),
        ],
        string='Tax Regime',
        default='common',
        help='Colombian tax regime classification for electronic invoicing.',
    )
    l10n_co_edi_fiscal_responsibilities = fields.Char(
        string='Fiscal Responsibilities',
        help='Comma-separated DIAN fiscal responsibility codes (e.g., O-13,O-15,O-23,O-47).',
    )
    l10n_co_edi_ciiu_code = fields.Char(
        string='CIIU Code',
        help='Primary CIIU (ISIC) economic activity code.',
    )

    # -- DIAN Service Endpoints (auto-set based on test_mode) --
    l10n_co_edi_test_set_id = fields.Char(
        string='DIAN Test Set ID',
        help='Test set identifier provided by DIAN during enablement process.',
    )

    @api.model
    def _l10n_co_edi_check_alerts(self):
        """Cron job: check certificate expiry and numbering range exhaustion.

        Logs warnings and can be extended to send notifications.
        """
        today = fields.Date.context_today(self)
        companies = self.search([
            ('account_fiscal_country_id.code', '=', 'CO'),
        ])

        for company in companies:
            # Check certificate expiry
            if company.l10n_co_edi_certificate_expiry:
                days_until_expiry = (company.l10n_co_edi_certificate_expiry - today).days
                if days_until_expiry <= 0:
                    _logger.error(
                        'Company %s: DIAN digital certificate has EXPIRED.',
                        company.name,
                    )
                elif days_until_expiry <= CERT_EXPIRY_WARN_DAYS:
                    _logger.warning(
                        'Company %s: DIAN digital certificate expires in %d days.',
                        company.name,
                        days_until_expiry,
                    )

            # Check numbering ranges on sale journals
            journals = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'sale'),
                ('l10n_co_edi_dian_range_to', '>', 0),
            ])
            for journal in journals:
                if journal.l10n_co_edi_range_remaining <= 0:
                    _logger.error(
                        'Company %s, Journal %s: DIAN numbering range EXHAUSTED.',
                        company.name,
                        journal.name,
                    )
                elif journal.l10n_co_edi_range_remaining <= RANGE_LOW_THRESHOLD:
                    _logger.warning(
                        'Company %s, Journal %s: Only %d numbers remaining in DIAN range.',
                        company.name,
                        journal.name,
                        journal.l10n_co_edi_range_remaining,
                    )

                # Check range validity
                if journal.l10n_co_edi_dian_range_valid_to and journal.l10n_co_edi_dian_range_valid_to < today:
                    _logger.error(
                        'Company %s, Journal %s: DIAN numbering range has EXPIRED (valid until %s).',
                        company.name,
                        journal.name,
                        journal.l10n_co_edi_dian_range_valid_to,
                    )
