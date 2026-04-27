# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class ResBank(models.Model):
    _inherit = "res.bank"

    country_code = fields.Char(related='country.code')
    l10n_jp_zengin_name_kana = fields.Char(string='Name (Kana)', help="Name of the bank in Kana.")
    l10n_jp_zengin_branch_name = fields.Char(string='Branch Name', help="Name of the branch of the bank.")
    l10n_jp_zengin_branch_name_kana = fields.Char(string='Branch Name (Kana)', help="Name of the branch of the bank in Kana.")
    l10n_jp_zengin_branch_code = fields.Char(string='Branch Code', help="Code of the branch of the bank.", size=3)

    @api.constrains('l10n_jp_zengin_branch_code')
    def _check_branch_code(self):
        for bank in self:
            if bank.l10n_jp_zengin_branch_code:
                if not bank.l10n_jp_zengin_branch_code.isdecimal():
                    raise ValidationError(_("Branch Code must be a number."))
                if len(bank.l10n_jp_zengin_branch_code) != 3:
                    raise ValidationError(_("Branch Code must be 3 digits long."))
