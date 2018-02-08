# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

from odoo.exceptions import ValidationError

from odoo.addons.base_iban.models.res_partner_bank import validate_iban
from odoo.addons.base.models.res_bank import sanitize_account_number

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # For bank journals
    l10n_ch_postal = fields.Char(related='bank_account_id.l10n_ch_postal')

    @api.onchange('bank_acc_number')
    def _onchange_set_l10n_ch_postal(self):
        try:
            validate_iban(self.bank_acc_number)
            is_iban = True
        except ValidationError:
            is_iban = False

        if is_iban:
            self.l10n_ch_postal = self.env['res.partner.bank'].retrieve_l10n_ch_postal(sanitize_account_number(self.bank_acc_number))
        else:
            self.l10n_ch_postal = self.bank_acc_number