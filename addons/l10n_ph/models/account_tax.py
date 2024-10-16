# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account


class AccountTax(account.AccountTax):

    l10n_ph_atc = fields.Char("Philippines ATC")
