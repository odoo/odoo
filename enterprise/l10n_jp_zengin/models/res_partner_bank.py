# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    l10n_jp_zengin_acc_holder_name_kana = fields.Char(string='Account Holder Name (Kana)', help="Name of the account holder in Kana.")
    l10n_jp_zengin_account_type = fields.Selection([
        ('regular', 'Regular'),
        ('current', 'Current'),
        ('savings', 'Savings'),
        ('other', 'Other')
    ], string='Account Type', default='regular')
    l10n_jp_zengin_bank_country_code = fields.Char(related="bank_id.country_code", string="JP: Country Code")
    l10n_jp_zengin_client_code = fields.Char(string='Client Code', help="Code of the client of the bank.", size=10)

    @api.constrains('l10n_jp_zengin_client_code')
    def _check_client_code(self):
        for account in self:
            if account.l10n_jp_zengin_client_code:
                if not account.l10n_jp_zengin_client_code.isdecimal():
                    raise ValidationError(_("Client Code must be a number."))
                if len(account.l10n_jp_zengin_client_code) != 10:
                    raise ValidationError(_("Client Code must be 10 digits long."))
