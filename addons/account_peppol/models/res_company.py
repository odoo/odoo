# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from stdnum import get_cc_module, ean

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.account.models.company import PEPPOL_LIST

try:
    import phonenumbers
except ImportError:
    phonenumbers = None


def _cc_checker(country_code, code_type):
    return lambda endpoint: get_cc_module(country_code, code_type).is_valid(endpoint)


def _re_sanitizer(expression):
    return lambda endpoint: (res.group(0) if (res := re.search(expression, endpoint)) else endpoint)


PEPPOL_ENDPOINT_RULES = {
    '0007': _cc_checker('se', 'orgnr'),
    '0088': ean.is_valid,
    '0184': _cc_checker('dk', 'cvr'),
    '0192': _cc_checker('no', 'orgnr'),
    '0208': _cc_checker('be', 'vat'),
}

PEPPOL_ENDPOINT_WARNINGS = {
    '0151': _cc_checker('au', 'abn'),
    '0201': lambda endpoint: bool(re.match('[0-9a-zA-Z]{6}$', endpoint)),
    '0210': _cc_checker('it', 'codicefiscale'),
    '0211': _cc_checker('it', 'iva'),
    '9906': _cc_checker('it', 'iva'),
    '9907': _cc_checker('it', 'codicefiscale'),
}

PEPPOL_ENDPOINT_SANITIZERS = {
    '0007': _re_sanitizer(r'\d{10}'),
    '0184': _re_sanitizer(r'\d{8}'),
    '0192': _re_sanitizer(r'\d{9}'),
    '0208': _re_sanitizer(r'\d{10}'),
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_peppol_contact_email = fields.Char(
        string='Primary contact email',
        compute='_compute_account_peppol_contact_email', store=True, readonly=False,
        help='Primary contact email for Peppol-related communication',
    )
    account_peppol_migration_key = fields.Char(string="Migration Key")
    account_peppol_phone_number = fields.Char(
        string='Mobile number',
        compute='_compute_account_peppol_phone_number', store=True, readonly=False,
        help='You will receive a verification code to this mobile number',
    )
    account_peppol_proxy_state = fields.Selection(
        selection=[
            ('not_registered', 'Not registered'),
            ('in_verification', 'In verification'),
            ('sender', 'Can send but not receive'),
            ('smp_registration', 'Can send, pending registration to receive'),
            ('receiver', 'Can send and receive'),
            ('rejected', 'Rejected'),
        ],
        string='PEPPOL status', required=True, default='not_registered',
    )
    peppol_eas = fields.Selection(related='partner_id.peppol_eas', readonly=False)
    peppol_endpoint = fields.Char(related='partner_id.peppol_endpoint', readonly=False)
    peppol_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='PEPPOL Purchase Journal',
        domain=[('type', '=', 'purchase')],
        compute='_compute_peppol_purchase_journal_id', store=True, readonly=False,
        inverse='_inverse_peppol_purchase_journal_id',
    )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _check_phonenumbers_import(self):
        if not phonenumbers:
            raise ValidationError(_("Please install the phonenumbers library."))

    def _sanitize_peppol_phone_number(self, phone_number=None):
        self.ensure_one()

        error_message = _(
            "Please enter the mobile number in the correct international format.\n"
            "For example: +32123456789, where +32 is the country code.\n"
            "Currently, only European countries are supported.")

        self._check_phonenumbers_import()

        phone_number = phone_number or self.account_peppol_phone_number
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

    def _check_peppol_endpoint_number(self, warning=False):
        self.ensure_one()
        peppol_dict = PEPPOL_ENDPOINT_WARNINGS if warning else PEPPOL_ENDPOINT_RULES

        return True if (endpoint_rule := peppol_dict.get(self.peppol_eas)) is None else endpoint_rule(self.peppol_endpoint)

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('account_peppol_phone_number')
    def _check_account_peppol_phone_number(self):
        for company in self:
            if company.account_peppol_phone_number:
                company._sanitize_peppol_phone_number()

    @api.constrains('peppol_endpoint')
    def _check_peppol_endpoint(self):
        for company in self:
            if not company.peppol_endpoint:
                continue
            if not company._check_peppol_endpoint_number(PEPPOL_ENDPOINT_RULES):
                raise ValidationError(_("The Peppol endpoint identification number is not correct."))

    @api.constrains('peppol_purchase_journal_id')
    def _check_peppol_purchase_journal_id(self):
        for company in self:
            if company.peppol_purchase_journal_id and company.peppol_purchase_journal_id.type != 'purchase':
                raise ValidationError(_("A purchase journal must be used to receive Peppol documents."))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('account_peppol_proxy_state')
    def _compute_peppol_purchase_journal_id(self):
        for company in self:
            if not company.peppol_purchase_journal_id and company.account_peppol_proxy_state not in ('not_registered', 'rejected'):
                company.peppol_purchase_journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'purchase'),
                ], limit=1)
                company.peppol_purchase_journal_id.is_peppol_journal = True
            else:
                company.peppol_purchase_journal_id = company.peppol_purchase_journal_id

    def _inverse_peppol_purchase_journal_id(self):
        for company in self:
            # This avoid having 2 or more journals from the same company with
            # `is_peppol_journal` set to True (which could occur after changes).
            journals_to_reset = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('is_peppol_journal', '=', True),
            ])
            journals_to_reset.is_peppol_journal = False
            company.peppol_purchase_journal_id.is_peppol_journal = True

    @api.depends('email')
    def _compute_account_peppol_contact_email(self):
        for company in self:
            if not company.account_peppol_contact_email:
                company.account_peppol_contact_email = company.email

    @api.depends('phone')
    def _compute_account_peppol_phone_number(self):
        for company in self:
            if not company.account_peppol_phone_number:
                try:
                    # precompute only if it's a valid phone number
                    company._sanitize_peppol_phone_number(company.phone)
                    company.account_peppol_phone_number = company.phone
                except ValidationError:
                    continue

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _sanitize_peppol_endpoint(self, vals, eas=False, endpoint=False):
        # TODO: remove in master
        if not (peppol_eas := vals.get('peppol_eas', eas)) or not (peppol_endpoint := vals.get('peppol_endpoint', endpoint)):
            return vals

        if sanitizer := PEPPOL_ENDPOINT_SANITIZERS.get(peppol_eas):
            vals['peppol_endpoint'] = sanitizer(peppol_endpoint)

        return vals

    @api.model
    def _sanitize_peppol_endpoint_in_values(self, values):
        eas = values.get('peppol_eas')
        endpoint = values.get('peppol_endpoint')
        if not eas or not endpoint:
            return
        if sanitizer := PEPPOL_ENDPOINT_SANITIZERS.get(eas):
            new_endpoint = sanitizer(endpoint)
            if new_endpoint:
                values['peppol_endpoint'] = new_endpoint

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sanitize_peppol_endpoint_in_values(vals)

        res = super().create(vals_list)
        if res:
            for company in res:
                self.env['ir.default'].sudo().set(
                    'res.partner',
                    'peppol_verification_state',
                    'not_verified',
                    company_id=company.id,
                )
        return res

    def write(self, vals):
        self._sanitize_peppol_endpoint_in_values(vals)
        return super().write(vals)

    # -------------------------------------------------------------------------
    # PEPPOL PARTICIPANT MANAGEMENT
    # -------------------------------------------------------------------------

    def _peppol_modules_document_types(self):
        """Override this function to add supported document types as modules are installed.

        :returns: dictionary of the form: {module_name: [(document identifier, document_name)]}
        """
        return {
            'default': {
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1":
                    "Peppol BIS Billing UBL Invoice V3",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1":
                    "Peppol BIS Billing UBL CreditNote V3",
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0::2.1":
                    "SI-UBL 2.0 Invoice",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0::2.1":
                    "SI-UBL 2.0 CreditNote",
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0::2.1":
                    "SG Peppol BIS Billing 3.0 Invoice",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0::2.1":
                    "SG Peppol BIS Billing 3.0 Credit Note",
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0::2.1":
                    "XRechnung UBL Invoice V2.0",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0::2.1":
                    "XRechnung UBL CreditNote V2.0",
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0::2.1":
                    "AU-NZ Peppol BIS Billing 3.0 Invoice",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0::2.1":
                    "AU-NZ Peppol BIS Billing 3.0 CreditNote",
            }
        }

    def _peppol_supported_document_types(self):
        """Returns a flattened dictionary of all supported document types."""
        return {
            identifier: document_name
            for module, identifiers in self._peppol_modules_document_types().items()
            for identifier, document_name in identifiers.items()
        }

    def _get_peppol_edi_mode(self):
        self.ensure_one()
        config_param = self.env['ir.config_parameter'].sudo().get_param('account_peppol.edi.mode')
        # by design, we can only have zero or one proxy user per company with type Peppol
        peppol_user = self.sudo().account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')
        demo_if_demo_identifier = 'demo' if self.peppol_eas == 'odemo' else False
        return demo_if_demo_identifier or peppol_user.edi_mode or config_param or 'prod'
