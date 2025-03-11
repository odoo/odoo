from odoo import fields, models


class InheritedModel(models.Model):
    _inherit = "res.users"

    property_ids = fields.One2many(
        "estate_property",
        "salesman",
        string="Properties",
        domain=[("state", "in", ["new", "offer_received"])],
    )
