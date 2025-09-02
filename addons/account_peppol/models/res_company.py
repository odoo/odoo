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
from odoo.addons.account_peppol.tools.demo_utils import handle_demo

try:
    import phonenumbers
except ImportError:
    phonenumbers = None


TIMEOUT = 10


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
            ('sender', 'Can send but not receive'),
            ('smp_registration', 'Can send, pending registration to receive'),
            ('receiver', 'Can send and receive'),
            ('rejected', 'Rejected'),
        ],
        string='PEPPOL status', required=True, default='not_registered',
    )
    peppol_identifier_ids = fields.One2many(
        comodel_name='res.partner.identification',
        related='partner_id.peppol_identifier_ids',
    )
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

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('account_peppol_phone_number')
    def _check_account_peppol_phone_number(self):
        for company in self:
            if company.account_peppol_phone_number:
                company._sanitize_peppol_phone_number()

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

    @api.depends('account_peppol_proxy_state')
    def _compute_peppol_can_send(self):
        can_send_domain = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        for company in self:
            company.peppol_can_send = company.account_peppol_proxy_state in can_send_domain

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
        peppol_user = self.sudo().account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')[:1]
        demo_if_demo_identifier = 'demo' if 'peppol_demo' in self.partner_id.peppol_identifier_ids.mapped('code') else False
        return demo_if_demo_identifier or peppol_user.edi_mode or config_param or 'prod'

    def _get_peppol_webhook_endpoint(self):
        self.ensure_one()
        return urljoin(self.get_base_url(), '/peppol/webhook')

    @handle_demo
    def _get_company_info_on_peppol(self, allow_raising=False):
        self.ensure_one()
        result = self.partner_id._peppol_fetch_partner_info(allow_raising=allow_raising)
        is_on_peppol, external_provider = result[self.partner_id.id]['is_on_peppol'], result[self.partner_id.id]['provider']
        error_msg = _(
            "A participant with these details has already been registered on the network. "
            "If you have previously registered to a Peppol service, please deregister."
        )
        if external_provider and "Odoo" not in external_provider:
            error_msg += _("The Peppol service that is used is %s.", external_provider)
        return {
            'is_on_peppol': is_on_peppol,
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
