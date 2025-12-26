from urllib.parse import urljoin

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.account.models.company import PEPPOL_LIST


class ResCompany(models.Model):
    _inherit = 'res.company'

    eracun_contact_email = fields.Char(
        string='eRacun Contact email',
        compute='_compute_eracun_contact_email', store=True, readonly=False,
        help='Primary contact email for eRacun-related communication',
    )
    l10n_hr_eracun_proxy_state = fields.Selection(
        selection=[
            ('not_registered', 'Not registered'),
            ('in_verification', 'In verification'), # Verification not used at the moment?
            ('receiver', 'Can send and receive'),
            ('rejected', 'Rejected'),
        ],
        string='eRacun proxy status', required=True, default='not_registered',
    )
    eracun_identifier_type = fields.Selection(related='partner_id.eracun_identifier_type', readonly=False)
    eracun_identifier_value = fields.Char(related='partner_id.eracun_identifier_value', readonly=False)
    # Not sure if a dedicated journal is required for Croatia, it probably has to do with reporting specifics
    eracun_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='eracun Purchase Journal',
        domain=[('type', '=', 'purchase')],
        compute='_compute_eracun_purchase_journal_id', store=True, readonly=False,
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    # Journal?
    @api.constrains('eracun_purchase_journal_id')
    def _check_eracun_purchase_journal_id(self):
        for company in self:
            if company.eracun_purchase_journal_id and company.eracun_purchase_journal_id.type != 'purchase':
                raise ValidationError(_("A purchase journal must be used to receive eRacun documents."))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    # Journal?
    @api.depends('l10n_hr_eracun_proxy_state')
    def _compute_eracun_purchase_journal_id(self):
        for company in self:
            if not company.eracun_purchase_journal_id and company.l10n_hr_eracun_proxy_state not in {'not_registered', 'rejected'}:
                company.eracun_purchase_journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'purchase'),
                ], limit=1)
                company.eracun_purchase_journal_id.is_eracun_journal = True
            else:
                company.eracun_purchase_journal_id = company.eracun_purchase_journal_id

    @api.depends('email')
    def _compute_eracun_contact_email(self):
        for company in self:
            if not company.eracun_contact_email:
                company.eracun_contact_email = company.email

    # -------------------------------------------------------------------------
    # PEPPOL PARTICIPANT MANAGEMENT
    # -------------------------------------------------------------------------

    def _get_eracun_edi_mode(self):
        self.ensure_one()
        config_param = self.env['ir.config_parameter'].sudo().get_param('l10n_hr_eracun.edi.mode')
        # by design, we can only have zero or one proxy user per company with type eRacun
        eracun_user = self.sudo().account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'eracun')
        return eracun_user.edi_mode or config_param or 'prod'

    def _get_eracun_webhook_endpoint(self):
        self.ensure_one()
        return urljoin(self.get_base_url(), '/eracun/webhook')



    # Likely unneeded since HR stuff uses a separate network from Peppol proper
    def _peppol_modules_document_types(self):
        document_types = super()._peppol_modules_document_types()
        document_types['default'].update({
            "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0":
                "HR UBL Invoice",
            "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0":
                "HR UBL CreditNote",
        })
        return document_types
