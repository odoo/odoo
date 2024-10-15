# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.addons import account


class AccountMove(account.AccountMove):

    taxable_supply_date = fields.Date()
