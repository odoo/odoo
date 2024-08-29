# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import account
from odoo import models, fields


class AccountMove(models.Model, account.AccountMove):

    taxable_supply_date = fields.Date()
