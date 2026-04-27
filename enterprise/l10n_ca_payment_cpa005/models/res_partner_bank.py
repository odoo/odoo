# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    l10n_ca_financial_institution_number = fields.Char(
        "Financial Institution ID Number",
        size=9,
        help="9-digit number that identifies the financial institution where the vendor holds an account. It typically "
        "starts with a 0, followed by a 3-digit institution number or ID, and a 5-digit branch routing number. This is a "
        "mandatory field for Canadian EFT file generation.",
    )

    @api.constrains("l10n_ca_financial_institution_number")
    def _check_l10n_ca_cpa005_financial_institution_number(self):
        for bank in self:
            financial_institution_number = bank.l10n_ca_financial_institution_number
            if financial_institution_number and (
                len(financial_institution_number) != 9 or not financial_institution_number.isdigit()
            ):
                raise ValidationError(
                    _(
                        'The Financial Institution ID Number of the "%s" bank account must be a 9 digit number. The '
                        "format is a 0, followed by a 3-digit institution number, and a 5-digit branch routing number.",
                        bank.display_name,
                    )
                )
