import re

from odoo import api, fields, models, _
from odoo.addons.l10n_uk_hmrc.models.res_company import validate_unique_taxpayer_reference
from odoo.exceptions import ValidationError

NIN_REGEX = re.compile(r'^[ABCEGHJKLMNOPRSTWXYZ][ABCEGHJKLMNPRSTWXYZ][0-9]{6}[A-D ]$')
CRN_REGEX = re.compile(r'^[A-Za-z]{2}[0-9]{1,6}|[0-9]{1,8}$')


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_uk_hmrc_unique_taxpayer_reference = fields.Char(string="Unique Taxpayer Reference")
    l10n_uk_hmrc_national_insurance_number = fields.Char(string="National Insurance Number")
    l10n_uk_hmrc_company_registration_number = fields.Char(string="Company Registration Number")

    @api.constrains('l10n_uk_hmrc_unique_taxpayer_reference')
    def _check_l10n_uk_hmrc_unique_taxpayer_reference(self):
        for partner in self:
            if partner.l10n_uk_hmrc_unique_taxpayer_reference:
                validate_unique_taxpayer_reference(partner.l10n_uk_hmrc_unique_taxpayer_reference)

    @api.constrains('l10n_uk_hmrc_national_insurance_number')
    def _check_l10n_uk_hmrc_national_insurance_number(self):
        for partner in self:
            if partner.l10n_uk_hmrc_national_insurance_number:
                if len(partner.l10n_uk_hmrc_national_insurance_number) == 8:  # Uk national insurance number can be 8 characters long in some cases, but the xml spec for the cis needs a length of 9 with an empty space if needed
                    partner.l10n_uk_hmrc_national_insurance_number += ' '
                if not NIN_REGEX.match(partner.l10n_uk_hmrc_national_insurance_number):
                    raise ValidationError(_("Invalid National Insurance Number."))

    @api.constrains('l10n_uk_hmrc_company_registration_number')
    def _check_l10n_uk_hmrc_company_registration_number(self):
        for partner in self:
            if partner.l10n_uk_hmrc_company_registration_number and not CRN_REGEX.match(partner.l10n_uk_hmrc_company_registration_number):
                raise ValidationError(_("Invalid National Insurance Number."))
