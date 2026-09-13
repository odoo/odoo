from odoo import fields, models


class ResPartnerIndustry(models.Model):
    _name = "res.partner.industry"
    _description = "Industry"
    _order = "name, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    full_name = fields.Char(translate=True)
    active = fields.Boolean(default=True)
