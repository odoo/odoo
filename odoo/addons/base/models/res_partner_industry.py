from odoo import fields, models


class ResPartnerIndustry(models.Model):
    _name = "res.partner.industry"
    _description = "Industry"
    _order = "name, id"

    name = fields.Char("Name", required=True, translate=True)
    full_name = fields.Char("Full Name", translate=True)
    active = fields.Boolean("Active", default=True)
