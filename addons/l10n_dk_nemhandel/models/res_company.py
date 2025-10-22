from urllib.parse import urljoin

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.account.models.company import PEPPOL_LIST

try:
    import phonenumbers
except ImportError:
    phonenumbers = None


class ResCompany(models.Model):
    _inherit = 'res.company'

    nemhandel_contact_email = fields.Char(
        string='Nemhandel Contact email',
        compute='_compute_nemhandel_contact_email', store=True, readonly=False,
        help='Primary contact email for Nemhandel-related communication',
    )
    nemhandel_phone_number = fields.Char(
        string='Nemhandel Phone number (for validation)',
        compute='_compute_nemhandel_phone_number', store=True, readonly=False,
        help='You will receive a verification code to this phone number',
    )
    l10n_dk_nemhandel_proxy_state = fields.Selection(
        selection=[
            ('not_registered', 'Not registered'),
            ('in_verification', 'In verification'),
            ('receiver', 'Can send and receive'),
            ('rejected', 'Rejected'),
        ],
        string='Nemhandel status', required=True, default='not_registered',
    )
    nemhandel_identifier_type = fields.Selection(related='partner_id.nemhandel_identifier_type', readonly=False)
    nemhandel_identifier_value = fields.Char(related='partner_id.nemhandel_identifier_value', readonly=False)
    nemhandel_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Nemhandel Purchase Journal',
        domain=[('type', '=', 'purchase')],
        compute='_compute_nemhandel_purchase_journal_id', store=True, readonly=False,
    )
    nemhandel_edi_user = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        compute='_compute_nemhandel_edi_user',
    )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _check_phonenumbers_import(self):
        if not phonenumbers:
            raise ValidationError(_("Please install the phonenumbers library."))

    def _sanitize_nemhandel_phone_number(self, phone_number=None):
        self.ensure_one()

        error_message = _(
            "Please enter the phone number in the correct international format.\n"
            "For example: +32123456789, where +32 is the country code.\n"
            "Currently, only European countries are supported."
        )

        self._check_phonenumbers_import()

        phone_number = phone_number or self.nemhandel_phone_number
        if not phone_number:
            return

        if not phone_number.startswith('+'):
            phone_number = f'+{phone_number}'

        try:
            phone_nbr = phonenumbers.parse(phone_number)
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValidationError(error_message)

        country_code = phonenumbers.phonenumberutil.region_code_for_number(phone_nbr)
        if country_code not in PEPPOL_LIST or not phonenumbers.is_valid_number(phone_nbr):
            raise ValidationError(error_message)

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('nemhandel_phone_number')
    def _check_nemhandel_phone_number(self):
        for company in self:
            if company.nemhandel_phone_number:
                company._sanitize_nemhandel_phone_number()

    @api.constrains('nemhandel_purchase_journal_id')
    def _check_nemhandel_purchase_journal_id(self):
        for company in self:
            if company.nemhandel_purchase_journal_id and company.nemhandel_purchase_journal_id.type != 'purchase':
                raise ValidationError(_("A purchase journal must be used to receive Nemhandel documents."))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_dk_nemhandel_proxy_state')
    def _compute_nemhandel_purchase_journal_id(self):
        for company in self:
            if not company.nemhandel_purchase_journal_id and company.l10n_dk_nemhandel_proxy_state not in {'not_registered', 'rejected'}:
                company.nemhandel_purchase_journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'purchase'),
                ], limit=1)
                company.nemhandel_purchase_journal_id.is_nemhandel_journal = True
            else:
                company.nemhandel_purchase_journal_id = company.nemhandel_purchase_journal_id

    @api.depends('email')
    def _compute_nemhandel_contact_email(self):
        for company in self:
            if not company.nemhandel_contact_email:
                company.nemhandel_contact_email = company.email

    @api.depends('phone')
    def _compute_nemhandel_phone_number(self):
        for company in self:
            if not company.nemhandel_phone_number:
                try:
                    # precompute only if it's a valid phone number
                    company._sanitize_nemhandel_phone_number(company.phone)
                    company.nemhandel_phone_number = company.phone
                except ValidationError:
                    continue

    @api.depends('account_edi_proxy_client_ids')
    def _compute_nemhandel_edi_user(self):
        for company in self:
            company.nemhandel_edi_user = company.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'nemhandel')

    # -------------------------------------------------------------------------
    # PEPPOL PARTICIPANT MANAGEMENT
    # -------------------------------------------------------------------------

    def _get_nemhandel_edi_mode(self):
        self.ensure_one()
        config_param = self.env['ir.config_parameter'].sudo().get_param('l10n_dk_nemhandel.edi.mode')
        return self.sudo().nemhandel_edi_user.edi_mode or config_param or 'prod'

    def _get_nemhandel_webhook_endpoint(self):
        self.ensure_one()
        return urljoin(self.get_base_url(), '/nemhandel/webhook')
