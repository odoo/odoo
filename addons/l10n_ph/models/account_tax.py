# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import account

from odoo import fields, models


class AccountTax(models.Model, account.AccountTax):

    l10n_ph_atc = fields.Char("Philippines ATC")
