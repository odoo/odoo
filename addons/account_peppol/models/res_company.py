# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from stdnum import get_cc_module, ean

from odoo import _, api, fields, models, modules, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import file_open, hash_sign, verify_hash_signed

from odoo.addons.account.models.company import PEPPOL_LIST
from ..tools.peppol_iap_connector import PeppolIAPConnector
from ..tools.demo_utils import DEMO_PRIVATE_KEY

try:
    import phonenumbers
except ImportError:
    phonenumbers = None


def _cc_checker(country_code, code_type):
    return lambda endpoint: get_cc_module(country_code, code_type).is_valid(endpoint)


def _re_sanitizer(expression):
    def _sanitize(endpoint):
        res = re.search(expression, endpoint)
        return res.group(0) if res else endpoint

    return _sanitize


PEPPOL_ENDPOINT_RULES = {
    '0007': _cc_checker('se', 'orgnr'),
    '0088': ean.is_valid,
    '0184': _cc_checker('dk', 'cvr'),
    '0192': _cc_checker('no', 'orgnr'),
    '0208': _cc_checker('be', 'vat'),
}

PEPPOL_ENDPOINT_WARNINGS = {
    '0151': _cc_checker('au', 'abn'),
    '0201': lambda endpoint: bool(re.match('[0-9a-zA-Z]{6}$', endpoint)),  # noqa: RUF039
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
        groups="base.group_user",
        string='Primary contact email',
        compute='_compute_account_peppol_contact_email', store=True, readonly=False,
        help='Primary contact email for Peppol-related communication',
    )
    account_peppol_phone_number = fields.Char(
        groups="base.group_user",
        string='Mobile number (for validation)',
        compute='_compute_account_peppol_phone_number', store=True, readonly=False,
        help='You will receive a verification code to this mobile number',
    )
    account_peppol_proxy_state = fields.Selection(
        groups="base.group_user",
        selection=[
            ('not_registered', 'Not registered'),
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('rejected', 'Rejected'),
            ('canceled', 'Canceled'),
        ],
        string='PEPPOL status', required=True, default='not_registered',
    )
    is_account_peppol_participant = fields.Boolean(groups="base.group_user", string='PEPPOL Participant')
    peppol_eas = fields.Selection(groups="base.group_user", related='partner_id.peppol_eas', readonly=False)
    peppol_endpoint = fields.Char(groups="base.group_user", related='partner_id.peppol_endpoint', readonly=False)
    peppol_purchase_journal_id = fields.Many2one(
        groups="base.group_user",
        comodel_name='account.journal',
        string='PEPPOL Purchase Journal',
        domain=[('type', '=', 'purchase')],
        compute='_compute_peppol_purchase_journal_id', store=True, readonly=False,
        inverse='_inverse_peppol_purchase_journal_id',
    )

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

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _sanitize_peppol_phone_number(self, phone_number=None):
        self.ensure_one()

        error_message = _(
            "Please enter the mobile number in the correct international format.\n"
            "For example: +32123456789, where +32 is the country code.\n"
            "Currently, only European countries are supported.")

        if not phonenumbers:
            raise ValidationError(_("Please install the phonenumbers library."))

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

    def _reset_peppol_configuration(self):
        """Reset all peppol configuration fields to their default value, as if not registered"""
        self.account_peppol_proxy_state = 'not_registered'
        self.partner_id._compute_peppol_eas()
        self.partner_id._compute_peppol_endpoint()

        # on 16.0 the constraints on account_edi_proxy_client.user prevent having multiple users of
        # type 'peppol' for the same company even if they are archived, so we need to unlink them
        self.account_edi_proxy_client_ids.unlink()

    def _check_peppol_endpoint_number(self, warning=False):
        self.ensure_one()
        peppol_dict = PEPPOL_ENDPOINT_WARNINGS if warning else PEPPOL_ENDPOINT_RULES
        endpoint_rule = peppol_dict.get(self.peppol_eas)

        return True if endpoint_rule is None else endpoint_rule(self.peppol_endpoint)

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
                    ('company_id', '=', company.id),
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
    def _sanitize_peppol_endpoint_in_values(self, values):
        eas = values.get('peppol_eas')
        endpoint = values.get('peppol_endpoint')
        if not eas or not endpoint:
            return
        sanitizer = PEPPOL_ENDPOINT_SANITIZERS.get(eas)
        if sanitizer:
            new_endpoint = sanitizer(endpoint)
            if new_endpoint:
                values['peppol_endpoint'] = new_endpoint

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sanitize_peppol_endpoint_in_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._sanitize_peppol_endpoint_in_values(vals)
        return super().write(vals)

    def _get_peppol_edi_mode(self):
        self.ensure_one()
        # by design, we can only have zero or one proxy user per company with type Peppol
        peppol_user = self.sudo().account_edi_proxy_client_ids.filtered(
            lambda u: u.company_id.id == self.id and u.edi_format_id.code == 'peppol'
        )
        return peppol_user._get_demo_state()

    def _peppol_generate_connect_token(self, peppol_identifier):
        self.ensure_one()
        msg = {
            'peppol_identifier': peppol_identifier,
            'company_id': self.id,
            'partner_id': self.env.user.partner_id.id,
            'create_at': str(fields.Datetime.now()),
        }
        return hash_sign(self.sudo().env, 'account_peppol_connect', msg, expiration_hours=24 * 7 * 2)

    @api.model
    def _peppol_decode_connect_token(self, token):
        if not token:
            return None
        try:
            payload = verify_hash_signed(self.sudo().env, 'account_peppol_connect', token)
        except (ValueError, TypeError):
            return None
        if not payload:
            return None
        peppol_identifier = payload.get('peppol_identifier')
        company = self.browse(payload.get('company_id')).exists()
        partner = self.env['res.partner'].browse(payload.get('partner_id')).exists()
        if not peppol_identifier or not company or not partner:
            return None
        return {
            'peppol_identifier': peppol_identifier,
            'company': company,
            'partner': partner,
        }

    def _peppol_can_connect(self, peppol_identifier):
        self.ensure_one()
        if self._get_peppol_edi_mode() == 'demo':
            return {'auth_required': False}
        base_url = self.get_base_url()
        return PeppolIAPConnector(self).can_connect(
            peppol_identifier=peppol_identifier,
            db_uuid=self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            callback_url=base_url + '/peppol/authentication/callback',
            webhook_url=base_url + '/peppol/authentication/webhook',
            connect_token=self._peppol_generate_connect_token(peppol_identifier),
            contact_email=self.account_peppol_contact_email,
        )

    @api.model
    def _peppol_select_kyc_url(self, can_connect_vals):
        if not can_connect_vals:
            raise UserError(_("Could not connect to Peppol proxy"))
        identifier_invalid = can_connect_vals.get('identifier_invalid')
        if identifier_invalid:
            code = identifier_invalid.get('code')
            if code == 'IDENTIFIER_NOT_ON_PEPPOL':
                raise UserError(_("Your identifier you entered is invalid for Peppol."))
            if code == 'IDENTIFIER_INCORRECT_FORMAT':
                if identifier_invalid.get('example'):
                    raise UserError(_("Your identifier does not have a valid format. Expected format: %s.", identifier_invalid.get('example')))
                raise UserError(_("Your identifier does not have a valid format."))
            raise UserError(_("Your identifier is invalid."))
        if can_connect_vals.get('db_invalid'):
            raise UserError(_("The database you are trying to connect to is not suitable for Peppol."))
        if not can_connect_vals.get('auth_required'):
            return None
        available_auths = can_connect_vals.get('available_auths') or {}
        auth = available_auths.get('generic') or next(iter(available_auths.values()), None)
        if not auth or not auth.get('authorization_url'):
            raise UserError(_("Authentication method is not available. Please contact Odoo support."))
        return auth['authorization_url']

    def _peppol_create_connection(self, peppol_identifier, auth_token=None):
        """Register though ``/api/peppol/2/connect`` and create proxy user record"""
        self.ensure_one()
        if self._get_peppol_edi_mode() == 'demo':
            edi_user = self.env['account_edi_proxy_client.user'].sudo().create({
                'id_client': f'demo{self.id}',
                'company_id': self.id,
                'edi_format_id': self.env.ref('account_peppol.edi_peppol').id,
                'edi_identification': peppol_identifier,
                'private_key': base64.b64encode(file_open(DEMO_PRIVATE_KEY, 'rb').read()),
                'refresh_token': 'demo',
            })
            self.account_peppol_proxy_state = 'active'
            return edi_user

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        private_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
        public_pem = private_key.public_key().public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
        response = PeppolIAPConnector(self).create_connection(
            peppol_identifier=peppol_identifier,
            db_uuid=self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            public_key=base64.b64encode(public_pem).decode(),
            auth_token=auth_token,
            peppol_company_name=self.display_name,
            peppol_company_vat=self.vat,
            peppol_company_street=self.street,
            peppol_company_city=self.city,
            peppol_company_zip=self.zip,
            peppol_country_code=self.country_id.code,
            peppol_phone_number=self.account_peppol_phone_number,
            peppol_contact_email=self.account_peppol_contact_email,
        )
        edi_user = self.env['account_edi_proxy_client.user'].sudo().create({
            'id_client': response['id_client'],
            'company_id': self.id,
            'edi_format_id': self.env.ref('account_peppol.edi_peppol').id,
            'edi_identification': peppol_identifier,
            'private_key': base64.b64encode(private_pem),
            'refresh_token': response['refresh_token'],
        })
        # map "new" /api/peppol/2/connect states into v16
        self.account_peppol_proxy_state = {
            'sender': 'pending',
            'smp_registration': 'pending',
            'receiver': 'active',
            'rejected': 'rejected',
        }.get(response['peppol_state'], 'not_registered')
        if not tools.config['test_enable'] and not modules.module.current_test:
            self.env.cr.commit()  # the user creation is not idempotent, the now exists and is commited on IAP
        return edi_user
