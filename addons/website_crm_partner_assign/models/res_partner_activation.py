from odoo import fields, models


class ResPartnerActivation(models.Model):
    _name = "res.partner.activation"
    _order = "sequence"
    _description = "Partner Activation"

    sequence = fields.Integer()
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
