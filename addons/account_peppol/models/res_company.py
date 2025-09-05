# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import re
import requests
from lxml import etree
from stdnum import get_cc_module, ean

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.urls import urljoin
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
TIMEOUT = 10


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_peppol_contact_email = fields.Char(
        string='Primary contact email',
        compute='_compute_account_peppol_contact_email', store=True, readonly=False,
        help='Primary contact email for Peppol connection related communications and notifications.\n'
             'In particular, this email is used by Odoo to reconnect your Peppol account in case of database change.',
    )
    account_peppol_migration_key = fields.Char(string="Migration Key")
    account_peppol_phone_number = fields.Char(
        string='Mobile number',
        compute='_compute_account_peppol_phone_number', store=True, readonly=False,
        help='This number is used for identification purposes only.',
    )
    account_peppol_proxy_state = fields.Selection(
        selection=[
            ('not_registered', 'Not registered'),
            ('sender', 'Can send but not receive'),
            ('smp_registration', 'Can send, pending registration to receive'),
            ('receiver', 'Can send and receive'),
            ('rejected', 'Rejected'),
        ],
        string='PEPPOL status', required=True, default='not_registered',
    )
    account_peppol_edi_user = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        compute='_compute_account_peppol_edi_user',
    )
    peppol_eas = fields.Selection(related='partner_id.peppol_eas', readonly=False)
    peppol_endpoint = fields.Char(related='partner_id.peppol_endpoint', readonly=False)
    peppol_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Peppol Purchase Journal',
        domain=[('type', '=', 'purchase')],
        compute='_compute_peppol_purchase_journal_id',
        store=True,
        readonly=False,
        inverse='_inverse_peppol_purchase_journal_id',
    )
    peppol_external_provider = fields.Char(tracking=True)
    peppol_can_send = fields.Boolean(compute='_compute_peppol_can_send')
    peppol_parent_company_id = fields.Many2one(comodel_name='res.company', compute='_compute_peppol_parent_company_id')
    # IAP-driven metadata with additive keys
    peppol_metadata = fields.Json(string='Peppol Metadata')
    peppol_metadata_updated_at = fields.Datetime(string='Peppol meta updated at')

    peppol_activate_self_billing_sending = fields.Boolean(
        string="Activate self-billing sending",
        help="If activated, you will be able to send vendor bills as self-billed invoices via Peppol.",
    )
    peppol_self_billing_reception_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Self-Billing reception journal',
        help="Any self-billed invoices / credit notes received via Peppol will be created in draft in this journal. Defaults to the first sale journal.",
        domain=[('type', '=', 'sale')],
        compute='_compute_peppol_self_billing_reception_journal_id',
        store=True,
        readonly=False,
        inverse='_inverse_peppol_self_billing_reception_journal_id',
    )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_active_peppol_parent_company(self):
        """
        Gets the closest parent company (relative from the current)
        that has an active peppol connection.
        :return: res.company record: containing single company if found, empty if not.
        """
        self.ensure_one()

        for parent_company in self.sudo().parent_ids[::-1][1:]:  # loop through parent companies starting from the closest parent
            if parent_company.sudo().peppol_can_send:
                return parent_company

        return self.env['res.company']

    def _have_unauthorized_peppol_parent_company(self):
        """
        Returns True if the company is using the active peppol connection of the parent company
        but the user does not have access to that parent company.
        """
        self.ensure_one()
        parent_company = self.peppol_parent_company_id
        return parent_company and parent_company not in self.env.user.company_ids

    def _reset_peppol_configuration(self, soft=False):
        """
        Reset all peppol configuration fields to their default value before registering.
        The EAS, endpoint, email, and phone number will be recomputed so that branch companies that uses
        their parent configuration can have their default values back
        (as these fields will be overwritten for them when they register as parent).

        :param soft: If True, will only set state to unregistered, but keep peppol config intact, so the user can register again
        """
        self.account_peppol_proxy_state = 'not_registered'
        self.account_peppol_migration_key = False
        if not soft:
            self.peppol_external_provider = False
            self.peppol_eas = False
            self.peppol_endpoint = False
            self.account_peppol_contact_email = False
            self.account_peppol_phone_number = False

            self._compute_account_peppol_contact_email()
            self._compute_account_peppol_phone_number()
        self.partner_id._compute_peppol_eas()
        self.partner_id._compute_peppol_endpoint()

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

    @api.depends('account_edi_proxy_client_ids')
    def _compute_account_peppol_edi_user(self):
        for company in self:
            company.account_peppol_edi_user = company.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')

    @api.depends('peppol_eas', 'peppol_endpoint')
    def _compute_peppol_parent_company_id(self):
        self.peppol_parent_company_id = False
        for company in self:
            for parent_company in company.parent_ids[::-1][1:]:
                if all((
                    company.peppol_eas,
                    company.peppol_endpoint,
                    company.peppol_eas == parent_company.peppol_eas,
                    company.peppol_endpoint == parent_company.peppol_endpoint,
                )):
                    company.peppol_parent_company_id = parent_company
                    break

    @api.depends('account_peppol_proxy_state')
    def _compute_peppol_purchase_journal_id(self):
        for company in self:
            if not company.peppol_purchase_journal_id and company.peppol_can_send:
                company.peppol_purchase_journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'purchase'),
                ], limit=1)
                company.peppol_purchase_journal_id.is_peppol_journal = True

    def _inverse_peppol_purchase_journal_id(self):
        for company in self:
            # This avoid having 2 or more purchase journals from the same company with
            # `is_peppol_journal` set to True (which could occur after changes).
            journals_to_reset = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'purchase'),
                ('is_peppol_journal', '=', True),
            ])
            journals_to_reset.is_peppol_journal = False
            company.peppol_purchase_journal_id.is_peppol_journal = True

    @api.depends('account_peppol_proxy_state')
    def _compute_peppol_self_billing_reception_journal_id(self):
        for company in self:
            if not company.peppol_self_billing_reception_journal_id and company.peppol_can_send:
                company.peppol_self_billing_reception_journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', 'sale'),
                ], limit=1)
                company.peppol_self_billing_reception_journal_id.is_peppol_journal = True

    def _inverse_peppol_self_billing_reception_journal_id(self):
        for company in self:
            # This avoid having 2 or more sale journals from the same company with
            # `is_peppol_journal` set to True (which could occur after changes).
            journals_to_reset = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'sale'),
                ('is_peppol_journal', '=', True),
            ])
            journals_to_reset.is_peppol_journal = False
            company.peppol_self_billing_reception_journal_id.is_peppol_journal = True

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

    @api.depends('account_peppol_proxy_state')
    def _compute_peppol_can_send(self):
        can_send_domain = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        for company in self:
            company.peppol_can_send = company.account_peppol_proxy_state in can_send_domain

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

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
                "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0::2.1": "Peppol BIS Self-Billing UBL Invoice V3",
                "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0::2.1": "Peppol BIS Self-Billing UBL CreditNote V3",
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

    def _get_peppol_edi_mode(self, temporary_eas=False):
        self.ensure_one()
        config_param = self.env['ir.config_parameter'].sudo().get_param('account_peppol.edi.mode')
        # by design, we can only have zero or one proxy user per company with type Peppol
        peppol_user = self.sudo().account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')
        demo_if_demo_identifier = 'demo' if (temporary_eas or self.peppol_eas) == 'odemo' else False
        return demo_if_demo_identifier or peppol_user.edi_mode or config_param or 'prod'

    def _get_peppol_webhook_endpoint(self):
        self.ensure_one()
        return urljoin(self.get_base_url(), '/peppol/webhook')

    def _get_company_info_on_peppol(self, edi_identification):

        def _get_peppol_provider(participant_info):
            service_metadata = participant_info.find('.//{*}ServiceMetadataReference')
            service_href = ''
            if service_metadata is not None:
                service_href = service_metadata.attrib.get('href', '')
            if not service_href:
                return None

            provider_name = None
            with contextlib.suppress(requests.exceptions.RequestException, etree.XMLSyntaxError):
                response = requests.get(service_href, timeout=TIMEOUT)
                if response.status_code == 200:
                    access_point_info = etree.fromstring(response.content)
                    provider_name = access_point_info.findtext('.//{*}ServiceDescription')
            return provider_name

        self.ensure_one()
        is_company_on_peppol = False
        external_provider = None
        error_msg = ''
        if (
            (participant_info := self.partner_id._get_participant_info(edi_identification)) is not None
            and (is_company_on_peppol := self.partner_id._check_peppol_participant_exists(participant_info, edi_identification))
        ):
            error_msg = _(
                "A participant with these details has already been registered on the network. "
                "If you have previously registered to a Peppol service, please deregister."
            )
            if (external_provider := _get_peppol_provider(participant_info)) and "Odoo" not in external_provider:
                error_msg += _("The Peppol service that is used is %s.", external_provider)
        return {
            'is_on_peppol': is_company_on_peppol,
            'external_provider': external_provider,
            'error_msg': error_msg,
        }

    def _account_peppol_send_welcome_email(self):
        self.ensure_one()
        if self.account_peppol_proxy_state not in ('sender', 'receiver'):
            return

        mail_template = self.env.ref('account_peppol.mail_template_peppol_registration', raise_if_not_found=False)
        if not mail_template:
            return

        mail_template.send_mail(self.id, force_send=True)
