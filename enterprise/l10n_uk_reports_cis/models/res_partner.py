import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

VRN_REGEX = re.compile(r'^V[0-9]{10}[A-HJ-NP-Z]{0,2}$')


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_uk_cis_enabled = fields.Boolean(default=False)

    l10n_uk_reports_cis_forename = fields.Char(
        string="Forename",
        compute='_compute_l10n_uk_cis_name_fields',
        readonly=False,
        store=True,
    )
    l10n_uk_reports_cis_second_forename = fields.Char(
        string="Second Forename",
        readonly=False,
        store=True,
    )
    l10n_uk_reports_cis_surname = fields.Char(
        string="Surname",
        compute='_compute_l10n_uk_cis_name_fields',
        readonly=False,
        store=True,
    )

    l10n_uk_reports_cis_verification_number = fields.Char(string="Verification Number", help="Ten digits number starting with 'V' provided by HMRC when verifying this partner")

    l10n_uk_reports_cis_deduction_rate = fields.Selection(
        [
            ('unmatched', "Unmatched (30%)"),
            ('net', "Net (20%)"),
            ('gross', "Gross (0%)")
        ],
        string="Deduction Rate",
        compute='_compute_l10n_uk_reports_cis_deduction_rate',
        precompute=True,
        required=True,
        readonly=False,
        store=True,
    )

    @api.constrains('l10n_uk_reports_cis_verification_number')
    def _check_l10n_uk_reports_cis_verification_number(self):
        for partner in self:
            if partner.l10n_uk_reports_cis_verification_number and not VRN_REGEX.match(partner.l10n_uk_reports_cis_verification_number):
                raise ValidationError(_("Invalid CIS Verification Number."))

    @api.constrains('l10n_uk_reports_cis_forename', 'is_company', 'l10n_uk_cis_enabled')
    def _check_partner_l10n_uk_reports_cis_forename(self):
        for partner in self:
            if not partner.is_company and not partner.l10n_uk_reports_cis_forename and partner.l10n_uk_cis_enabled:
                raise UserError(_("When a partner is an individual, a forename needs to be set."))

    @api.constrains('l10n_uk_reports_cis_surname', 'is_company', 'l10n_uk_cis_enabled')
    def _check_partner_l10n_uk_reports_cis_surname(self):
        for partner in self:
            if not partner.is_company and not partner.l10n_uk_reports_cis_surname and partner.l10n_uk_cis_enabled:
                raise UserError(_("When a partner is an individual, a surname needs to be set."))

    @api.depends('l10n_uk_reports_cis_verification_number')
    def _compute_l10n_uk_reports_cis_deduction_rate(self):
        for partner in self:
            if not partner.l10n_uk_reports_cis_verification_number:
                partner.l10n_uk_reports_cis_deduction_rate = 'unmatched'

    @api.depends('company_type', 'name', 'l10n_uk_cis_enabled')
    def _compute_l10n_uk_cis_name_fields(self):
        for partner in self:
            if partner.company_type not in 'person' or partner.l10n_uk_reports_cis_forename or partner.l10n_uk_reports_cis_surname\
                or not partner.name or not partner.l10n_uk_cis_enabled:
                continue

            partner_split_name = partner.name.split(' ')
            if len(partner_split_name) == 2:
                partner.l10n_uk_reports_cis_forename = partner_split_name[0]
                partner.l10n_uk_reports_cis_surname = partner_split_name[1]

    def _get_deduction_amount_from_rate(self):
        self.ensure_one()
        if self.l10n_uk_reports_cis_deduction_rate == 'unmatched':
            return -30.0
        elif self.l10n_uk_reports_cis_deduction_rate == 'net':
            return -20.0
        return 0.0
