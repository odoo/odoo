# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

SARIE_CODE_LENGTH = 4


class ResBank(models.Model):
    _inherit = 'res.bank'

    l10n_sa_sarie_code = fields.Char(string='Bank SARIE ID', size=SARIE_CODE_LENGTH)
    # Ref. http://www.sama.gov.sa/
    l10n_sa_bank_establishment_code = fields.Char(string="Bank Establishment ID", help="ID of the Establishment registered with the bank")

    @api.constrains('l10n_sa_sarie_code')
    def _check_l10n_sa_sarie_code(self):
        for bank in self:
            if not bank.l10n_sa_sarie_code:
                continue
            if len(bank.l10n_sa_sarie_code) != SARIE_CODE_LENGTH:
                raise ValidationError(_("Bank SARIE ID length must be 4 letters."))
            if not bank.l10n_sa_sarie_code.isalpha() or not bank.l10n_sa_sarie_code.isupper():
                raise ValidationError(_("Bank SARIE ID can only contain upper case English alphabets."))
