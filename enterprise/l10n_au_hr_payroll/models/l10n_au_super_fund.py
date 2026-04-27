# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nAuSuperFund(models.Model):
    _name = "l10n_au.super.fund"
    _description = "Super Fund"

    display_name = fields.Char(string="Name", required=True)
    abn = fields.Char(string="ABN", required=True)
    address_id = fields.Many2one("res.partner", string="Address", required=True)
    fund_type = fields.Selection([
        ("APRA", "APRA"),
        ("SMSF", "SMSF"),
    ], default="APRA", string="Type", required=True)
    usi = fields.Char(string="USI", help="Unique Superannuation Identifier")
    esa = fields.Char(string="ESA", help="Electronic Service Address")
