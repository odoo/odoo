import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

AOR_REGEX = re.compile(r'^[0-9]{3}P[A-Z][0-9]{7}[0-9X]$')
UTR_REGEX = re.compile(r'^[0-9]{10}$')


def validate_unique_taxpayer_reference(utr):
    """
    Check that the unique taxpayer reference number is valid

    Regex: ^[0-9]{10}$
    Example: 4307982374
    """

    if not UTR_REGEX.match(utr):
        raise ValidationError(_("Invalid Unique Taxpayer Reference. A valid format contains only 10 numbers."))


class ResCompany(models.Model):
    _inherit = "res.company"
    ################################
    ##      HMRC credentials      ##
    ################################
    l10n_uk_hmrc_sender_id = fields.Char(string="Sender ID")
    l10n_uk_hmrc_tax_office_number = fields.Char(string="Tax office number")
    l10n_uk_hmrc_tax_office_reference = fields.Char(string="Tax office reference")

    ##########################
    ##      HMRC fields     ##
    ##########################
    l10n_uk_hmrc_unique_taxpayer_reference = fields.Char(
        string="Unique Taxpayer Reference",
        groups='account.group_account_manager',
    )
    l10n_uk_hmrc_account_office_reference = fields.Char(
        string="Account Office Reference",
        groups='account.group_account_manager',
    )

    @api.constrains('l10n_uk_hmrc_unique_taxpayer_reference')
    def _check_l10n_uk_hmrc_unique_taxpayer_reference(self):
        for company in self:
            if company._has_hmrc_field_filled():
                if not company.l10n_uk_hmrc_unique_taxpayer_reference:
                    raise ValidationError(_("Company Unique Taxpayer Reference should be filled."))
                validate_unique_taxpayer_reference(company.l10n_uk_hmrc_unique_taxpayer_reference)

    @api.constrains('l10n_uk_hmrc_account_office_reference')
    def _check_l10n_uk_hmrc_account_office_reference(self):
        for company in self:
            if company._has_hmrc_field_filled():
                if not company.l10n_uk_hmrc_account_office_reference:
                    raise ValidationError(_("Company Account Office Reference should be filled."))
                if not AOR_REGEX.match(company.l10n_uk_hmrc_account_office_reference):
                    raise ValidationError(_("Invalid Account Office Reference."))

    @api.constrains('l10n_uk_hmrc_sender_id')
    def _check_l10n_uk_hmrc_sender_id(self):
        for company in self:
            if company._has_hmrc_field_filled() and not company.l10n_uk_hmrc_sender_id:
                raise ValidationError(_("Company HMRC sender id should be filled."))

    @api.constrains('l10n_uk_hmrc_tax_office_number')
    def _check_l10n_uk_hmrc_tax_office_number(self):
        for company in self:
            if company._has_hmrc_field_filled() and not company.l10n_uk_hmrc_tax_office_number:
                raise ValidationError(_("Company HMRC tax office number should be filled."))

    @api.constrains('l10n_uk_hmrc_tax_office_reference')
    def _check_l10n_uk_hmrc_tax_office_reference(self):
        for company in self:
            if company._has_hmrc_field_filled() and not company.l10n_uk_hmrc_tax_office_reference:
                raise ValidationError(_("Company HMRC tax office reference should be filled."))

    def _has_hmrc_field_filled(self):
        self.ensure_one()
        return (
            self.l10n_uk_hmrc_unique_taxpayer_reference
            or self.l10n_uk_hmrc_account_office_reference
            or self.l10n_uk_hmrc_sender_id
            or self.l10n_uk_hmrc_tax_office_number
            or self.l10n_uk_hmrc_tax_office_reference
        )
