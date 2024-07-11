# -*- coding: utf-8 -*-
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


PEPPOL_ENDPOINT_RULES = {
    '0007': ['se', 'orgnr'],
    '0088': ['ean'],
    '0184': ['dk', 'cvr'],
    '0192': ['no', 'orgnr'],
    '0208': ['be', 'vat'],
}

PEPPOL_ENDPOINT_WARNING = {
    '0201': ['regex', '[0-9a-zA-Z]{6}$'],
    '0210': ['it', 'codicefiscale'],
    '0211': ['it', 'iva'],
    '9906': ['it', 'iva'],
    '9907': ['it', 'codicefiscale'],
    '0151': ['au', 'abn'],
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
        string='Mobile number (for validation)',
        compute='_compute_account_peppol_phone_number', store=True, readonly=False,
        help='You will receive a verification code to this mobile number',
    )
    account_peppol_proxy_state = fields.Selection(
        selection=[
            ('not_registered', 'Not registered'),
            ('not_verified', 'Not verified'),
            ('sent_verification', 'Verification code sent'),
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('rejected', 'Rejected'),
            ('canceled', 'Canceled'),
        ],
        string='PEPPOL status', required=True, default='not_registered',
    )
    is_account_peppol_participant = fields.Boolean(string='PEPPOL Participant')
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

    def _check_peppol_endpoint_number(self, warning=False):
        self.ensure_one()

        peppol_dict = PEPPOL_ENDPOINT_WARNING if warning else PEPPOL_ENDPOINT_RULES
        endpoint_rule = peppol_dict.get(self.peppol_eas)
        if not endpoint_rule:
            return True

        if endpoint_rule[0] == 'regex':
            return bool(re.match(endpoint_rule[1], self.peppol_endpoint))

        if endpoint_rule[0] == 'ean':
            check_module = ean
        else:
            check_module = get_cc_module(endpoint_rule[0], endpoint_rule[1])
        return check_module.is_valid(self.peppol_endpoint)

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
        if 'peppol_eas' not in vals and 'peppol_endpoint' not in vals:
            return vals

        peppol_eas = vals['peppol_eas'] if 'peppol_eas' in vals else eas # let users remove the value
        peppol_endpoint = vals['peppol_endpoint'] if 'peppol_endpoint' in vals else endpoint
        if not peppol_eas or not peppol_endpoint:
            return vals

        if peppol_eas == '0208':
            cbe_match = re.search('[0-9]{10}', peppol_endpoint)
            if bool(cbe_match):
                vals['peppol_endpoint'] = cbe_match.group(0)
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals = self._sanitize_peppol_endpoint(vals)
        return super().create(vals_list)

    def write(self, vals):
        for company in self:
            vals = self._sanitize_peppol_endpoint(vals, company.peppol_eas, company.peppol_endpoint)
        return super().write(vals)
