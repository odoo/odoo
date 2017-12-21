# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # For bank journals
    l10n_ch_postal_manual = fields.Char(string='Manual ISR Reference', related='bank_account_id.l10n_ch_postal_manual', help="Your account reference to generate ISR. Leave blank to directly use you account number, or to use the last 12 characters of your account number if it is a swiss IBAN.")
