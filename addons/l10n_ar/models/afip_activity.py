from odoo import fields, models


class AccountActivity(models.Model):
    _name = "afip.activity"
    _description = "afip.activity"

    code = fields.Char(required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
