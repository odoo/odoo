# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    check_number = fields.Char(
        string="Check Number",
        related='payment_id.check_number',
    )
